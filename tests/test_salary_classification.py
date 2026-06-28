import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.classification_agent import classify_applicant

# Test profiles — only salary changes
BASE_PROFILE = {
    "full_name": "Test User",
    "age": "35",
    "nationality": "Indian",
    "occupation": "Software Engineer",
    "anzsco_code": "261313",
    "qualification": "Bachelor's / Honours",
    "job_offer": True,
    "salary": None,  # overridden per test
    "years_experience": "5",
    "nz_work_experience_years": "0",
    "english_level": "IELTS 7.0",
    "currently_in_nz": True,
    "family": "None"
}

TEST_CASES = [
    {"salary": 72999, "expected_pillar_points": 3, "label": "S1 - Below median → qualification pillar"},
    {"salary": 73000,   "expected_pillar_points": 3, "label": "S2 - 1x median floor"},
    {"salary": 109499,  "expected_pillar_points": 3, "label": "S3 - 1x median ceiling"},
    {"salary": 109500,  "expected_pillar_points": 4, "label": "S4 - 1.5x median floor"},
    {"salary": 145999,  "expected_pillar_points": 4, "label": "S5 - 1.5x median ceiling"},
    {"salary": 146000,  "expected_pillar_points": 5, "label": "S6 - 2x median floor"},
    {"salary": 148000,  "expected_pillar_points": 5, "label": "S7 - 2x median mid"},
    {"salary": 218999,  "expected_pillar_points": 5, "label": "S8 - 2x median ceiling"},
    {"salary": 219000,  "expected_pillar_points": 6, "label": "S9 - 3x median floor"},
]

# ── Qualification boundary tests ──────────────────────────────
QUALIFICATION_TEST_CASES = [
    {"qualification": "Diploma / Certificate", "expected_pillar_points": 0, "salary": "60000", "label": "Q1 - Diploma → 0pts qualification"},
    {"qualification": "Bachelor's / Honours", "expected_pillar_points": 3, "salary": "60000", "label": "Q2 - Bachelor's → 3pts"},
    {"qualification": "Masters / Postgraduate", "expected_pillar_points": 4, "salary": "60000", "label": "Q3 - Masters → 4pts"},
    {"qualification": "PhD / Doctorate", "expected_pillar_points": 5, "salary": "60000", "label": "Q4 - PhD → 5pts"},
]

# ── Age boundary tests ─────────────────────────────────────────
AGE_TEST_CASES = [
    {"age": "54", "expected_status": "ELIGIBLE", "label": "A1 - Age 54 → eligible"},
    {"age": "55", "expected_status": "ELIGIBLE", "label": "A2 - Age 55 → eligible (boundary)"},
    {"age": "56", "expected_status": "NOT_ELIGIBLE", "label": "A3 - Age 56 → not eligible"},
]

# ── Job offer tests ────────────────────────────────────────────
JOB_OFFER_TEST_CASES = [
    {"job_offer": True, "expected_status": "ELIGIBLE", "label": "J1 - Job offer present → eligible"},
    {"job_offer": False, "expected_status": "NOT_ELIGIBLE", "label": "J2 - No job offer → not eligible"},
]

# ── NZ experience tests ────────────────────────────────────────
NZ_EXP_TEST_CASES = [
    {"nz_exp": "0", "expected_exp_points": 0, "label": "E1 - 0yr NZ exp → 0pts"},
    {"nz_exp": "1", "expected_exp_points": 1, "label": "E2 - 1yr NZ exp → 1pt"},
    {"nz_exp": "2", "expected_exp_points": 2, "label": "E3 - 2yr NZ exp → 2pts"},
    {"nz_exp": "3", "expected_exp_points": 3, "label": "E4 - 3yr NZ exp → 3pts (max)"},
    {"nz_exp": "4", "expected_exp_points": 3, "label": "E5 - 4yr NZ exp → 3pts (capped)"},
]

def run_tests():
    print("\n🧪 Running Salary Classification Tests\n")
    passed = 0
    failed = 0

    for tc in TEST_CASES:
        profile = BASE_PROFILE.copy()
        profile["salary"] = str(tc["salary"])

        result = classify_applicant(profile)
        parsed = result.get("parsed", {})

        actual_points = int(parsed.get("pillar_points", -1))
        expected_points = tc["expected_pillar_points"]
        pillar = parsed.get("pillar", "unknown")

        status = "✅ PASS" if actual_points == expected_points else "❌ FAIL"
        if actual_points == expected_points:
            passed += 1
        else:
            failed += 1

        print(f"{status} | {tc['label']}")
        print(f"       Salary: ${tc['salary']:,} | Pillar: {pillar} | Expected: {expected_points}pts | Got: {actual_points}pts\n")

    print(f"Results: {passed}/{len(TEST_CASES)} passed")
    return passed, len(TEST_CASES)

def run_qualification_tests():
    print("\n🧪 Running Qualification Boundary Tests\n")
    passed = 0
    failed = 0
    for tc in QUALIFICATION_TEST_CASES:
        profile = BASE_PROFILE.copy()
        profile["qualification"] = tc["qualification"]
        profile["salary"] = tc["salary"]
        result = classify_applicant(profile)
        parsed = result.get("parsed", {})
        actual_points = int(parsed.get("pillar_points", -1))
        expected_points = tc["expected_pillar_points"]
        status = "✅ PASS" if actual_points == expected_points else "❌ FAIL"
        if actual_points == expected_points:
            passed += 1
        else:
            failed += 1
        print(f"{status} | {tc['label']}")
        print(f"       Qualification: {tc['qualification']} | Expected: {expected_points}pts | Got: {actual_points}pts\n")
    print(f"Results: {passed}/{len(QUALIFICATION_TEST_CASES)} passed")
    return passed, len(QUALIFICATION_TEST_CASES)

def run_age_tests():
    print("\n🧪 Running Age Boundary Tests\n")
    passed = 0
    failed = 0
    for tc in AGE_TEST_CASES:
        profile = BASE_PROFILE.copy()
        profile["age"] = tc["age"]
        profile["salary"] = "150000"
        profile["nz_work_experience_years"] = "1"
        profile["qualification"] = "Masters / Postgraduate"
        result = classify_applicant(profile)
        parsed = result.get("parsed", {})
        actual_status = parsed.get("status", "UNKNOWN")
        expected_status = tc["expected_status"]
        status = "✅ PASS" if actual_status == expected_status else "❌ FAIL"
        if actual_status == expected_status:
            passed += 1
        else:
            failed += 1
        print(f"{status} | {tc['label']}")
        print(f"       Age: {tc['age']} | Expected: {expected_status} | Got: {actual_status}\n")
    print(f"Results: {passed}/{len(AGE_TEST_CASES)} passed")
    return passed, len(AGE_TEST_CASES)

def run_job_offer_tests():
    print("\n🧪 Running Job Offer Tests\n")
    passed = 0
    failed = 0
    for tc in JOB_OFFER_TEST_CASES:
        profile = BASE_PROFILE.copy()
        profile["job_offer"] = tc["job_offer"]
        profile["salary"] = "150000"
        profile["nz_work_experience_years"] = "1"
        profile["qualification"] = "Masters / Postgraduate"
        result = classify_applicant(profile)
        parsed = result.get("parsed", {})
        actual_status = parsed.get("status", "UNKNOWN")
        expected_status = tc["expected_status"]
        status = "✅ PASS" if actual_status == expected_status else "❌ FAIL"
        if actual_status == expected_status:
            passed += 1
        else:
            failed += 1
        print(f"{status} | {tc['label']}")
        print(f"       Job Offer: {tc['job_offer']} | Expected: {expected_status} | Got: {actual_status}\n")
    print(f"Results: {passed}/{len(JOB_OFFER_TEST_CASES)} passed")
    return passed, len(JOB_OFFER_TEST_CASES)

def run_nz_exp_tests():
    print("\n🧪 Running NZ Experience Tests\n")
    passed = 0
    failed = 0
    for tc in NZ_EXP_TEST_CASES:
        profile = BASE_PROFILE.copy()
        profile["nz_work_experience_years"] = tc["nz_exp"]
        profile["salary"] = "120000"
        result = classify_applicant(profile)
        parsed = result.get("parsed", {})
        actual_exp = int(parsed.get("nz_experience_points", -1))
        expected_exp = tc["expected_exp_points"]
        status = "✅ PASS" if actual_exp == expected_exp else "❌ FAIL"
        if actual_exp == expected_exp:
            passed += 1
        else:
            failed += 1
        print(f"{status} | {tc['label']}")
        print(f"       NZ Exp: {tc['nz_exp']}yr | Expected: {expected_exp}pts | Got: {actual_exp}pts\n")
    print(f"Results: {passed}/{len(NZ_EXP_TEST_CASES)} passed")
    return passed, len(NZ_EXP_TEST_CASES)

if __name__ == "__main__":
    s_pass, s_total = run_tests()
    q_pass, q_total = run_qualification_tests()
    a_pass, a_total = run_age_tests()
    j_pass, j_total = run_job_offer_tests()
    e_pass, e_total = run_nz_exp_tests()
    
    total_pass = s_pass + q_pass + a_pass + j_pass + e_pass
    total_cases = s_total + q_total + a_total + j_total + e_total
    print(f"\n🎯 OVERALL: {total_pass}/{total_cases} passed")