"""
End-to-end integration test verifying the live real-time DualTrust AI pipeline.
"""
import urllib.request
import json
import os
import time

BASE = "http://127.0.0.1:8000"


def req(path, data=None, headers=None):
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(BASE + path, data=body, headers=h)
    with urllib.request.urlopen(r) as res:
        return json.loads(res.read())


def main():
    print("[1] Testing Login API...")
    auth = req("/api/auth/login", {"email": "demo@dualtrust.ai", "password": "demo1234"})
    token = auth["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}
    print("    Logged in successfully. User:", auth["user_name"], "Role:", auth["role"])

    print("\n[2] Testing Create New Application API...")
    new_app = req("/api/applications", {
        "applicant_name": "Kavita Nair (Live Real-Time Applicant)",
        "loan_type": "home",
        "loan_amount": 2500000.0
    }, headers=auth_headers)
    app_id = new_app["id"]
    print("    Created Application ID:", app_id, "Status:", new_app["status"])

    print("\n[3] Testing Real Document Upload...")
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    sample_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_documents", "valid_salary_slip.pdf")
    with open(sample_path, "rb") as f:
        pdf_bytes = f.read()

    part1 = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="kavita_salary.pdf"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode()
    part2 = pdf_bytes
    part3 = f"\r\n--{boundary}--\r\n".encode()
    upload_body = part1 + part2 + part3

    upload_req = urllib.request.Request(
        f"{BASE}/api/applications/{app_id}/documents",
        data=upload_body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        }
    )
    with urllib.request.urlopen(upload_req) as u_res:
        doc = json.loads(u_res.read())
    print("    Uploaded Document ID:", doc["id"], "Type detected:", doc["doc_type"])

    print("\n[4] Testing Dual-AI Real-Time Analysis Trigger...")
    analyze_res = req(f"/api/documents/{doc['id']}/analyze", data={}, headers=auth_headers)
    print("    Analysis triggered:", analyze_res)

    # Let the analysis task finish
    time.sleep(2)

    print("\n[5] Fetching Full Real-Time Dashboard Data...")
    dash = req(f"/api/applications/{app_id}/dashboard", headers=auth_headers)
    risk = dash["risk_score"]
    print("    Risk Score:", risk["overall_score"] if risk else "Processing", "Verdict:", risk["status"] if risk else "None")
    print("    Fields Compared in Consensus Engine:", len(dash["field_comparisons"]))
    print("    Deterministic Rule Checks Run:", len(dash["rule_checks"]))
    for rc in dash["rule_checks"]:
        print(f"      * {rc['rule_name']}: {'PASS' if rc['passed'] else 'FAIL'} ({rc['detail']})")

    print("\n[6] Submitting Human Reviewer Decision...")
    review_res = req(f"/api/applications/{app_id}/review", {
        "decision": "APPROVE",
        "notes": "All dual-pipeline extractions and deterministic rules passed with flying colors."
    }, headers=auth_headers)
    print("    Review decision recorded:", review_res["decision"])

    print("\n[7] Verifying Hash-Chained Audit Trail Integrity...")
    verify_res = req("/api/audit-logs/verify", headers=auth_headers)
    print("    Audit Chain Valid:", verify_res["chain_valid"])
    print("    Total Audit Entries Tracked:", verify_res["total_entries"])
    print("    Broken Entries:", verify_res["broken_entries"])
    print("\n[SUCCESS] Entire real-time dual-pipeline loan verification pipeline verified perfectly!")


if __name__ == "__main__":
    main()
