import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import fitz

# Set before importing app: tests never read or change the production database.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["APP_PASSWORD"] = "test-admin-password"
os.environ["ANALYST_PASSWORD"] = "test-analyst-password"
os.environ.pop("RENDER", None)
os.environ.pop("COOKIE_SECURE", None)
os.environ.pop("APP_USERS_JSON", None)
from app.main import app
from app.database import Base, get_db, engine
from app.models import Application, LoginSession
from app.schemas import FinancialInput
from app.services.risk_service import assess
from app.services.document_service import extract_document_data, validate_document
from app.services.ai_service import generate_brief

test_url = os.getenv('TEST_DATABASE_URL', 'sqlite://')
if test_url != 'sqlite://':
    from sqlalchemy.engine import make_url
    if make_url(test_url).database != 'creditos_test':
        raise RuntimeError('Integration tests only allow a database named creditos_test')
test_engine = create_engine(test_url, **({'connect_args': {'check_same_thread': False}, 'poolclass': StaticPool} if test_url == 'sqlite://' else {}))
Session = sessionmaker(bind=test_engine)
def test_db():
    with Session() as db:
        yield db
app.dependency_overrides[get_db] = test_db

PAYLOAD = {"name": "Comercial Ejemplo", "rfc": "ABC010101AB1", "address": "Calle Centro 100 Ciudad",
           "monthly_income": 35000, "monthly_debt": 3000, "bank_seniority_months": 24,
           "requested_amount": 50000, "term_months": 24, "annual_rate": 24}
HEADERS = {"X-Credit-Request": "1"}

def pdf(text):
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((50, 50), text)
        return doc.tobytes()

class Workflows(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(test_engine)
        Base.metadata.create_all(test_engine)
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def login(self, user="admin"):
        password = "test-admin-password" if user == "admin" else "test-analyst-password"
        response = self.client.post("/auth/login", json={"username": user, "password": password})
        self.assertEqual(response.status_code, 200, response.text)
        self.client.headers.update(HEADERS)

    def create(self, **changes):
        response = self.client.post("/applications/", json={**PAYLOAD, **changes})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_private_routes_and_public_shell(self):
        for path in ("/applications/", "/dashboard/metrics", "/scorecredito", "/applications/export.csv"):
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertIn("frame-ancestors", self.client.get("/").headers["content-security-policy"])

    def test_login_csrf_logout_and_revocation(self):
        self.login()
        token = self.client.cookies.get("credit_session")
        self.client.headers.pop("X-Credit-Request")
        self.assertEqual(self.client.post("/applications/", json=PAYLOAD).status_code, 403)
        self.client.headers.update(HEADERS)
        self.assertEqual(self.client.post("/auth/logout").status_code, 200)
        self.client.cookies.set("credit_session", token)
        self.assertEqual(self.client.get("/applications/").status_code, 401)

    def test_login_rate_limit(self):
        for _ in range(10):
            self.assertEqual(self.client.post("/auth/login", json={"username":"admin","password":"wrong"}).status_code, 401)
        self.assertEqual(self.client.post("/auth/login", json={"username":"admin","password":"wrong"}).status_code, 429)

    def test_unconfigured_access_closed(self):
        with patch.dict(os.environ, {"APP_PASSWORD": ""}):
            self.assertEqual(self.client.post("/auth/login", json={"username":"admin","password":""}).status_code, 503)

    def test_individual_users_roles_and_revocation(self):
        import hashlib
        salt = 'ab' * 16
        hashed = hashlib.pbkdf2_hmac('sha256', b'individual-password', bytes.fromhex(salt), 600000).hex()
        users = {'ana': {'role': 'admin', 'password_hash': f'pbkdf2_sha256$600000${salt}${hashed}'}}
        with patch.dict(os.environ, {'APP_USERS_JSON': json.dumps(users)}):
            response = self.client.post('/auth/login', json={'username':'ana','password':'individual-password'})
            self.assertEqual(response.status_code, 200, response.text)
            self.client.headers.update(HEADERS)
            case = self.create()
            audit = self.client.get(f'/applications/{case["id"]}').json()['audit']
            self.assertEqual(audit[0]['actor'], 'ana')
            users['ana']['role'] = 'analyst'
            with patch.dict(os.environ, {'APP_USERS_JSON': json.dumps(users)}):
                self.assertEqual(self.client.get('/auth/me').json()['role'], 'analyst')
            users = {'other': users['ana']}
            with patch.dict(os.environ, {'APP_USERS_JSON': json.dumps(users)}):
                self.assertEqual(self.client.get('/auth/me').status_code, 401)
        with patch.dict(os.environ, {'APP_USERS_JSON': 'invalid'}):
            self.assertEqual(self.client.post('/auth/login',json={'username':'admin','password':'test-admin-password'}).status_code,503)

    def test_tiny_rate_is_stable(self):
        result = assess(FinancialInput(monthly_income=35000,bank_seniority_months=24,annual_rate=1e-20,requested_amount=12000,term_months=12))
        self.assertEqual(result['monthly_payment'],1000)

    def test_chunked_body_limit(self):
        self.login()
        def chunks():
            for _ in range(10):
                yield b'x' * (1024 * 1024)
        response = self.client.post('/applications/', content=chunks())
        self.assertEqual(response.status_code, 413)

    def test_validation_and_nonfinite(self):
        self.login()
        for changes in ({"monthly_income":0},{"monthly_debt":-1},{"term_months":0},{"rfc":"invalid"},{"name":"   "},{"address":" "},{"annual_rate":101}):
            self.assertEqual(self.client.post("/applications/", json={**PAYLOAD, **changes}).status_code,422)
        self.assertEqual(self.client.post("/applications/", content=json.dumps({**PAYLOAD,"monthly_income":float("inf")})).status_code,422)

    def test_deterministic_no_protected_attributes(self):
        self.login()
        first = self.create()
        second = self.create(name="Otra Persona", gender="F", curp="DIFFERENT")
        self.assertEqual(first["assessment"], second["assessment"])
        self.assertEqual(first["status"],"REVIEW")
        self.assertLessEqual(first["score"],100)
        zero = assess(FinancialInput(monthly_income=10000,bank_seniority_months=24,requested_amount=12000,term_months=12,annual_rate=0))
        self.assertEqual(zero["monthly_payment"],1000)
        self.assertEqual(zero["max_amount"],42000)

    def test_document_decision_audit_and_stale_version(self):
        self.login()
        c = self.create()
        decision = {"decision":"APPROVED","note":"Evidencia revisada por responsable.","version":1}
        self.assertEqual(self.client.post(f'/applications/{c["id"]}/review',json=decision).status_code,409)
        raw=pdf("Nombre: Comercial Ejemplo\nDireccion: Calle Centro 100 Ciudad\nRFC: ABC010101AB1\nVigencia: 31/12/2099")
        response=self.client.post(f'/applications/{c["id"]}/documents',files={"file":("../../outside.pdf",raw,"application/pdf")})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["document_verified"],"MATCHED")
        self.assertEqual(response.json()["application"]["version"],2)
        self.assertEqual(self.client.post(f'/applications/{c["id"]}/review',json=decision).status_code,409)
        decision["version"]=2
        self.assertEqual(self.client.post(f'/applications/{c["id"]}/review',json=decision).status_code,200)
        response=self.client.get(f'/applications/{c["id"]}').json()
        self.assertEqual(response["status"],"APPROVED")
        self.assertEqual(len(response["audit"]),3)
        # A replacement document reopens a previously decided application.
        response=self.client.post(f'/applications/{c["id"]}/documents',files={"file":("new.pdf",raw,"application/pdf")})
        self.assertEqual(response.json()["application"]["status"],"REVIEW")

    def test_analyst_cannot_decide(self):
        self.login("analyst")
        c=self.create()
        self.assertEqual(self.client.post(f'/applications/{c["id"]}/review',json={"decision":"REJECTED","note":"Revisado por el analista.","version":1}).status_code,403)

    def test_document_errors_and_extraction(self):
        self.login()
        c=self.create(monthly_income=5000)
        for content in (b"not pdf",b"%PDF-xxx",b"x"*(8*1024*1024+1)):
            response=self.client.post(f'/applications/{c["id"]}/documents',files={"file":("bad.pdf",content)})
            self.assertIn(response.status_code,(413,422))
        raw=pdf("Nombre: Comercial Ejemplo\nDireccion: Calle Centro 100 Ciudad\nIngreso mensual: 35,000\nAntiguedad bancaria: 24\nVigencia: 01/01/2020")
        d=self.client.post("/applications/extract-document",files={"file":("a.pdf",raw)}).json()
        self.assertTrue(d["requires_confirmation"])
        self.assertEqual(d["monthly_income"],35000)
        response=self.client.post(f'/applications/{c["id"]}/documents',files={"file":("a.pdf",raw)}).json()
        self.assertEqual(response["document_verified"],"REVIEW")
        self.assertIn("Documento vencido",response["application"]["rejection_reason"])
        self.assertIn("Ingreso mínimo",response["application"]["rejection_reason"])

    def test_metrics_pagination_search_export(self):
        self.login()
        for i in range(12):
            self.create(name="Cliente "+str(i))
        self.create(name="=HYPERLINK(malicious)")
        result=self.client.get("/applications/?page_size=5&page=2").json()
        self.assertEqual(result["total"],13)
        self.assertEqual(len(result["items"]),5)
        self.assertEqual(self.client.get("/applications/?search=Cliente%2011").json()["total"],1)
        self.assertEqual(self.client.get("/applications/?search=%25").json()["total"],0)
        metrics=self.client.get("/dashboard/metrics").json()
        self.assertEqual(metrics["review"],13)
        self.assertEqual(metrics["requested_volume"],650000)
        export=self.client.get("/applications/export.csv")
        self.assertIn("'=HYPERLINK",export.text)
        self.assertNotIn("ABC010101AB1",export.text)

    def test_copilot_minimizes_data_and_fallback(self):
        self.login()
        c=self.create()
        with patch("app.routes.applications.generate_brief",return_value={"text":"borrador","provider":"openai","generated":True}) as mock:
            response=self.client.post(f'/applications/{c["id"]}/copilot',json={"task":"summary"})
            self.assertEqual(response.status_code,200)
            context=json.dumps(mock.call_args.args[0])
            for value in ("Comercial Ejemplo","ABC010101AB1","Calle Centro"):
                self.assertNotIn(value,context)
        with patch.dict(os.environ,{"OPENAI_API_KEY":""}):
            response=self.client.post(f'/applications/{c["id"]}/copilot',json={"task":"checklist"})
            self.assertEqual(response.json()["provider"],"local")
            self.assertFalse(response.json()["generated"])

    def test_external_ai_failure_and_request_contract(self):
        context={"assessment":assess(FinancialInput(monthly_income=35000,bank_seniority_months=24))}
        with patch.dict(os.environ,{"OPENAI_API_KEY":"test-key"}):
            with patch("urllib.request.urlopen",side_effect=TimeoutError):
                self.assertEqual(generate_brief(context,"summary")["provider"],"local")
            payload={"output":[{"type":"message","content":[{"type":"output_text","text":"Resumen generado."}]}]}
            with patch("urllib.request.urlopen",return_value=io.BytesIO(json.dumps(payload).encode())) as mock:
                self.assertTrue(generate_brief(context,"summary")["generated"])
                request=json.loads(mock.call_args.args[0].data)
                self.assertFalse(request["store"])

    def test_legacy_data_preserved(self):
        self.login()
        with Session() as db:
            old=Application(name="Histórico",rfc="OLD010101AB1",curp="",gender="X",monthly_income=12000,
                            bank_seniority_months=24,address="Calle Vieja 1",score=800,status="APPROVED")
            db.add(old);db.commit();old_id=old.id
        row=self.client.get(f"/applications/{old_id}").json()
        self.assertIsNone(row["assessment"])
        self.assertEqual(row["score"],800)
        self.assertEqual(self.client.post(f"/applications/{old_id}/review",json={"decision":"REJECTED","note":"Cambiar caso histórico.","version":1}).status_code,409)

if __name__ == "__main__":
    unittest.main()
