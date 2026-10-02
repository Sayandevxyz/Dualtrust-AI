"""pytest tests — M6 Cross-Document Verification"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal, Base, engine
from app.models import (
    Application, Document, Extraction, CrossDocumentCheck,
    ApplicationStatus, DocumentType
)
from app.services.cross_doc_verifier import run_cross_document_verification


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_matching_income_across_docs_passes(db_session):
    app = Application(
        id="test-cross-001",
        applicant_name="Sunil Sharma",
        loan_type="home",
        loan_amount=1000000.0,
    )
    db_session.add(app)
    db_session.flush()

    doc_salary = Document(
        id="doc-s-001",
        application_id=app.id,
        doc_type=DocumentType.salary_slip,
        file_path="/tmp/sal.pdf",
        file_hash="hash1",
    )
    doc_bank = Document(
        id="doc-b-001",
        application_id=app.id,
        doc_type=DocumentType.bank_statement,
        file_path="/tmp/bank.pdf",
        file_hash="hash2",
    )
    db_session.add_all([doc_salary, doc_bank])
    db_session.flush()

    # Both show ~60k monthly
    db_session.add(Extraction(
        document_id=doc_salary.id,
        engine="groq",
        structured_json={"applicant_name": "Sunil Sharma", "net_salary": 60000.0, "account_number": "12345678"},
        overall_confidence=0.95
    ))
    db_session.add(Extraction(
        document_id=doc_bank.id,
        engine="groq",
        structured_json={"account_holder_name": "Sunil Sharma", "average_monthly_credit": 60500.0, "account_number": "12345678"},
        overall_confidence=0.95
    ))
    db_session.commit()

    checks = run_cross_document_verification(app.id, db_session)
    income_check = next((c for c in checks if "salary_vs_bank" in c.check_type), None)
    assert income_check is not None
    assert income_check.result == "OK"


def test_large_income_gap_salary_vs_itr_flagged(db_session):
    app = Application(
        id="test-cross-002",
        applicant_name="Vikas Gupta",
        loan_type="business",
        loan_amount=2000000.0,
    )
    db_session.add(app)
    db_session.flush()

    doc_salary = Document(
        id="doc-s-002",
        application_id=app.id,
        doc_type=DocumentType.salary_slip,
        file_path="/tmp/sal2.pdf",
        file_hash="hash3",
    )
    doc_itr = Document(
        id="doc-i-002",
        application_id=app.id,
        doc_type=DocumentType.itr,
        file_path="/tmp/itr2.pdf",
        file_hash="hash4",
    )
    db_session.add_all([doc_salary, doc_itr])
    db_session.flush()

    # Gross salary 1,00,000/mo = 12 LPA, but ITR shows 5 LPA (>50% gap)
    db_session.add(Extraction(
        document_id=doc_salary.id,
        engine="groq",
        structured_json={"applicant_name": "Vikas Gupta", "gross_salary": 100000.0, "pan_number": "ABCDE1234F"},
        overall_confidence=0.9
    ))
    db_session.add(Extraction(
        document_id=doc_itr.id,
        engine="groq",
        structured_json={"applicant_name": "Vikas Gupta", "gross_total_income": 500000.0, "pan_number": "ABCDE1234F"},
        overall_confidence=0.9
    ))
    db_session.commit()

    checks = run_cross_document_verification(app.id, db_session)
    itr_check = next((c for c in checks if "salary_vs_itr" in c.check_type), None)
    assert itr_check is not None
    assert itr_check.result == "DISCREPANCY"
    assert itr_check.discrepancy_pct > 20.0


def test_mismatched_pan_across_docs_flagged(db_session):
    app = Application(
        id="test-cross-003",
        applicant_name="Deepak Sen",
        loan_type="personal",
        loan_amount=500000.0,
    )
    db_session.add(app)
    db_session.flush()

    doc_pan = Document(
        id="doc-p-003",
        application_id=app.id,
        doc_type=DocumentType.pan_card,
        file_path="/tmp/pan.pdf",
        file_hash="hash5",
    )
    doc_salary = Document(
        id="doc-s-003",
        application_id=app.id,
        doc_type=DocumentType.salary_slip,
        file_path="/tmp/sal3.pdf",
        file_hash="hash6",
    )
    db_session.add_all([doc_pan, doc_salary])
    db_session.flush()

    db_session.add(Extraction(
        document_id=doc_pan.id,
        engine="groq",
        structured_json={"applicant_name": "Deepak Sen", "pan_number": "ABCDE1234F"},
        overall_confidence=0.9
    ))
    db_session.add(Extraction(
        document_id=doc_salary.id,
        engine="groq",
        structured_json={"applicant_name": "Deepak Sen", "pan_number": "XYZAB5678C"},
        overall_confidence=0.9
    ))
    db_session.commit()

    checks = run_cross_document_verification(app.id, db_session)
    pan_check = next((c for c in checks if "pan_cross_match" in c.check_type), None)
    assert pan_check is not None
    assert pan_check.result == "DISCREPANCY"
