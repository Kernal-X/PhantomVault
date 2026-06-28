import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agents.generation.generation_agent import generate
from agents.generation.cache import clear_cache



def run_test_case(path, metadata):
    print("=" * 80)
    print(f"REQUESTED PATH: {path}")
    print(f"METADATA: {metadata}")
    print("-" * 80)

    result = generate(path, metadata)

    print(f"SUCCESS : {result['success']}")
    print(f"SOURCE  : {result['source']}")
    print(f"SCHEMA  : {result['schema']}")
    print(f"REASON  : {result['reason']}")
    print("-" * 80)
    print("GENERATED CONTENT:\n")
    print(result["content"])
    print("=" * 80)
    print("\n\n")


if __name__ == "__main__":
    # TEST CASE 1: Payroll CSV
    # run_test_case(
    #     path="/shared/finance/payroll_march.csv",
    #     metadata={
    #         "file_type": "csv",
    #         "content_type": "salary_data",
    #         "size": "15kb",
    #         "realism_level": "high",
    #         "use_llm_realism": False,
    #         "columns": []
    #     }
    # )

    # # TEST CASE 2: Credentials TXT
    # run_test_case(
    #     path="/shared/admin/backup_credentials.txt",
    #     metadata={
    #         "file_type": "txt",
    #         "content_type": "credentials",
    #         "size": "5kb",
    #         "realism_level": "medium",
    #         "use_llm_realism": True,
    #         "columns": []
    #     }
    # )

    # TEST CASE 3: Logs
    run_test_case(
        path="/shared/logs/security_audit.log",
        metadata={
            "file_type": "log",
            "content_type": "logs",
            "size": "20kb",
            "realism_level": "high",
            "use_llm_realism": True,
            "columns": []
        }
    )

    # # TEST CASE 4: Internal Note
    # run_test_case(
    #     path="/shared/operations/vendor_notes.txt",
    #     metadata={
    #         "file_type": "txt",
    #         "content_type": "internal_note",
    #         "size": "3kb",
    #         "realism_level": "high",
    #         "use_llm_realism": True,
    #         "columns": []
    #     }
    # )

    # # TEST CASE 5: ENV File
    # run_test_case(
    #     path="/shared/config/.env",
    #     metadata={
    #         "file_type": "txt",
    #         "content_type": "env",
    #         "size": "2kb",
    #         "realism_level": "high",
    #         "use_llm_realism": True,
    #         "columns": []
    #     }
    # )

    # # TEST CASE 6: JSON Data
    # run_test_case(
    #     path="/shared/hr/employee_archive.json",
    #     metadata={
    #         "file_type": "json",
    #         "content_type": "employee_data",
    #         "size": "20kb",
    #         "realism_level": "medium",
    #         "use_llm_realism": True,
    #         "columns": []
    #     }
    # )

    # TEST CASE 7: SQL Dump
    # run_test_case(
    #     path="/shared/db/payroll_backup.sql",
    #     metadata={
    #         "file_type": "sql",
    #         "content_type": "payroll_db",
    #         "size": "40kb",
    #         "realism_level": "high",
    #         "use_llm_realism": False,
    #         "columns": []
    #     }
    # )