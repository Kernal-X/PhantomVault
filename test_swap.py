import os
from agents.deployment.deployment_agent import DeploymentManager

import sys

def run_test():
    # 1. Target a "real" sensitive file
    if len(sys.argv) > 1:
        real_file = sys.argv[1]
        if not os.path.exists(real_file):
            print(f"[ERROR] The file {real_file} does not exist!")
            return
        print(f"[TEST] Targeting your REAL file at: {real_file}")
        
        # Determine file type for the mock strategy
        ext = os.path.splitext(real_file)[1].lower().replace(".", "")
        file_type = ext if ext in ["csv", "json", "txt", "log", "env", "sql"] else "txt"
    else:
        test_dir = r"C:\shared\finance_test"
        real_file = os.path.join(test_dir, "payroll.csv")
        file_type = "csv"
        
        os.makedirs(test_dir, exist_ok=True)
        with open(real_file, "w") as f:
            f.write("id,name,salary,bonus\n")
            f.write("1,Alice,250000,50000\n")
            f.write("2,Bob,180000,20000\n")
            
        print(f"[TEST] Created REAL sensitive file at: {real_file}")
        print("[TEST] Real file contents:")
        with open(real_file, "r") as f:
            print(f.read())
            
    print("-" * 50)
    
    # 2. Simulate the AI generating a plan to trap the attacker on this exact file
    from agents.generation.generation_agent import GenerationAgent
    gen_agent = GenerationAgent()
    manager = DeploymentManager(generation_agent=gen_agent)
    
    # Mock the LLM output targeting our real file
    mock_strategy = {
        "execution_plan": {
            "files_to_create": [
                {
                    "absolute_path": real_file,
                    "file_type": file_type,
                    "content_profile": f"{file_type}_financial_summary",
                    "realism": "high"
                }
            ]
        }
    }
    
    print("[TEST] Running Deployment Agent to deploy decoys...")
    manager.deploy(mock_strategy, materialize_files=True)
    
    print("-" * 50)
    
    # 3. Verify the Swap!
    print(f"[TEST] Let's see what the hacker sees when they open: {real_file}")
    with open(real_file, "r", encoding="utf-8") as f:
        content = f.read()
        if len(content) > 150:
            print(content[:150] + "\n... [TRUNCATED for readability] ...")
        else:
            print(content)
        
    vault_file = real_file + ".aads_vault"
    if os.path.exists(vault_path := vault_file): # os.path.exists sees hidden files
        print(f"\n[SUCCESS] The real file was vaulted to: {vault_file}")
        
        # Check if it's hidden!
        import ctypes
        attrs = ctypes.windll.kernel32.GetFileAttributesW(vault_file)
        if attrs != -1 and (attrs & 0x02):
            print("[SUCCESS] The vaulted file is hidden via NTFS cloaking! It will not show up in Explorer.")
    else:
        print("\n[FAILED] The real file was not vaulted!")
        
    print("-" * 50)
    print("[TEST] Now calling the Automated Recovery to restore everything...")
    manager.restore_vaults()
    
    print("-" * 50)
    print(f"[TEST] Final check. Does the real file still exist? {os.path.exists(real_file)}")
    with open(real_file, "r", encoding="utf-8") as f:
        content = f.read()
        if len(content) > 150:
            print(content[:150] + "\n... [TRUNCATED for readability] ...")
        else:
            print(content)

if __name__ == "__main__":
    run_test()
