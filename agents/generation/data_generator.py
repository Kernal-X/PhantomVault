import random
import json
from datetime import datetime, timedelta
import os
import io
import csv
import string

print("DEBUG FILE LOADED:", __file__)

# ----------------------------
# GLOBAL DATA (fallback values)
# ----------------------------

FIRST_NAMES = [
    "Aarav", "Neha", "Rohan", "Priya", "Karan", "Ananya",
    "Rahul", "Ishita", "Vikram", "Meera", "Aditya",
    "Sneha", "Dev", "Kavya", "Arjun", "Nikhil",
    "Pooja", "Simran", "Varun", "Tanvi", "Aditi",
    "Harsh", "Ritika", "Yash", "Sanya"
]

LAST_NAMES = [
    "Singh", "Verma", "Mehta", "Shah", "Joshi", "Rao",
    "Kapoor", "Malhotra", "Sethi", "Nair", "Bansal",
    "Iyer", "Menon", "Patel", "Sharma", "Chopra",
    "Khanna", "Tiwari", "Agarwal", "Kulkarni"
]

DEPARTMENTS = [
    "Finance", "HR", "Engineering", "Operations",
    "Admin", "Security", "Compliance", "Procurement",
    "Legal", "IT Support"
]

BANKS = ["HDFC Bank", "ICICI Bank", "State Bank of India", "Axis Bank", "Kotak Mahindra Bank"]

EMAIL_DOMAINS = ["corp.local", "internal.corp", "mail.corp.local"]

LOG_LEVELS = ["INFO", "WARN", "ERROR", "DEBUG"]

LOG_ACTIONS = [
    "login success",
    "payroll export initiated",
    "backup completed",
    "finance report downloaded",
    "vendor sync completed",
    "credential validation passed",
    "access policy updated",
    "restricted folder reviewed",
    "privileged session approved",
    "account reconciliation completed"
]

PROJECTS = ["Orion", "Atlas", "Helios", "Nimbus", "Phoenix", "Vega", "Aurora"]

ROLE_MAP = {
    "Finance": ["Finance Analyst", "Senior Finance Analyst", "Finance Manager"],
    "HR": ["HR Executive", "HR Manager", "Recruiter"],
    "Engineering": ["Software Engineer", "Senior Engineer", "Tech Lead"],
    "Operations": ["Operations Analyst", "Operations Manager", "Coordinator"],
    "Admin": ["Admin Executive", "Office Manager", "Coordinator"],
    "Security": ["Security Analyst", "SOC Engineer", "Security Manager"],
    "Compliance": ["Compliance Analyst", "Risk Officer", "Compliance Manager"],
    "Procurement": ["Procurement Executive", "Vendor Manager", "Sourcing Analyst"],
    "Legal": ["Legal Associate", "Compliance Counsel", "Legal Manager"],
    "IT Support": ["Support Engineer", "IT Administrator", "Systems Analyst"]
}

SENSITIVITY_EXTRA_FIELDS = {
    "low": [],
    "medium": ["email", "department", "role"],
    "high": ["email", "phone", "account_id", "last_login", "is_active"]
}

# ----------------------------
# OPTIONAL GLOBAL CONTEXT LOADER
# ----------------------------

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOBAL_CONTEXT_PATH = os.path.join(BASE_DIR, "context", "global_context.json")


def load_global_context():
    if not os.path.exists(GLOBAL_CONTEXT_PATH):
        return {
            "departments": DEPARTMENTS,
            "email_domains": EMAIL_DOMAINS,
            "project_names": PROJECTS
        }

    try:
        with open(GLOBAL_CONTEXT_PATH, "r") as f:
            data = json.load(f)

        return {
            "departments": data.get("departments", DEPARTMENTS),
            "email_domains": data.get("email_domains", EMAIL_DOMAINS),
            "project_names": data.get("project_names", PROJECTS)
        }
    except Exception:
        return {
            "departments": DEPARTMENTS,
            "email_domains": EMAIL_DOMAINS,
            "project_names": PROJECTS
        }


# ----------------------------
# HELPERS
# ----------------------------

def sanitize_sql_identifier(name):
    if not name:
        return "field_name"

    safe = str(name).strip().lower()
    safe = safe.replace(" ", "_").replace("-", "_")
    safe = "".join(ch for ch in safe if ch.isalnum() or ch == "_")

    if not safe:
        safe = "field_name"

    if safe[0].isdigit():
        safe = f"col_{safe}"

    return safe


def random_date(days_back=365):
    days_ago = random.randint(1, days_back)
    dt = datetime.now() - timedelta(
        days=days_ago,
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
        seconds=random.randint(0, 59)
    )
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def random_email(name, domains):
    username = name.lower().replace(" ", ".")
    return f"{username}@{random.choice(domains)}"


def random_password(sensitivity="medium"):
    if sensitivity == "high":
        base = random.choice(["Admin", "Secure", "Backup", "FinOps", "Access", "ProdOps"])
        return f"{base}@{random.randint(1000,9999)}!"
    base = random.choice(["Internal", "Access", "Ops", "Secure"])
    return f"{base}@{random.randint(100,999)}"


def random_ifsc():
    return f"{random.choice(['HDFC','ICIC','SBIN','UTIB'])}{random.randint(100000,999999)}"


def random_aws_access_key():
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "AKIA" + "".join(random.choices(chars, k=16))


def random_phone():
    return f"9{random.randint(100000000, 999999999)}"


def random_account_id(prefix="ACC"):
    return f"{prefix}{random.randint(100000, 999999)}"


def random_bank_account():
    return "".join(random.choices(string.digits, k=12))


def random_pan():
    letters = "".join(random.choices(string.ascii_uppercase, k=5))
    digits = "".join(random.choices(string.digits, k=4))
    suffix = random.choice(string.ascii_uppercase)
    return f"{letters}{digits}{suffix}"


def random_ip():
    return f"10.{random.randint(1,20)}.{random.randint(1,250)}.{random.randint(2,250)}"


def random_host():
    return random.choice([
        "srv-app-01", "srv-app-02", "srv-fin-01", "db-core-01",
        "backup-node-02", "ops-console-01"
    ])


def salary_by_department(dept):
    bands = {
        "Finance": (85000, 170000),
        "HR": (60000, 120000),
        "Engineering": (95000, 185000),
        "Operations": (70000, 135000),
        "Admin": (55000, 110000),
        "Security": (90000, 180000),
        "Compliance": (80000, 160000),
        "Procurement": (70000, 140000),
        "Legal": (95000, 190000),
        "IT Support": (65000, 130000)
    }
    low, high = bands.get(dept, (70000, 140000))
    return random.randint(low, high)


def parse_size_to_bytes(size_value):
    if not size_value:
        return 5 * 1024

    s = str(size_value).strip().lower()

    legacy_map = {
        "small": 5 * 1024,
        "medium": 25 * 1024,
        "large": 100 * 1024
    }

    if s in legacy_map:
        return legacy_map[s]

    try:
        if s.endswith("kb"):
            return int(float(s[:-2].strip()) * 1024)
        elif s.endswith("mb"):
            return int(float(s[:-2].strip()) * 1024 * 1024)
        elif s.endswith("b"):
            return int(float(s[:-1].strip()))
        else:
            return int(float(s))
    except Exception:
        return 5 * 1024


def estimate_row_count(size_bytes, file_type="csv", column_count=5):
    column_count = max(1, column_count)

    if file_type == "csv":
        avg_row_size = max(70, column_count * 20)
    elif file_type == "json":
        avg_row_size = max(120, column_count * 30)
    elif file_type == "sql":
        avg_row_size = max(140, column_count * 35)
    elif file_type in {"log", "txt", "env"}:
        avg_row_size = 90
    else:
        avg_row_size = 80

    rows = max(2, size_bytes // avg_row_size)
    return min(rows, 5000)


def maybe_enrich_schema(schema, metadata):
    """
    Only enrich tiny / fallback-like schemas.
    Avoid mutating explicit well-defined schemas.
    """
    sensitivity = metadata.get("sensitivity", "medium").lower()
    schema = schema[:] if schema else []

    if len(schema) >= 4:
        return schema

    existing = {col.lower() for col in schema}

    for field in SENSITIVITY_EXTRA_FIELDS.get(sensitivity, []):
        if field.lower() not in existing:
            schema.append(field)

    return schema


def infer_table_name(path, metadata):
    filename = os.path.basename(path).lower()
    content_type = metadata.get("content_type", "").lower()

    if content_type:
        return sanitize_sql_identifier(content_type)

    filename = filename.replace(".sql", "").replace(".dump", "").replace(".bak", "")
    filename = filename.replace("-", "_").replace(" ", "_")

    return sanitize_sql_identifier(filename if filename else "records")


def infer_sql_types(schema):
    type_map = {}

    for field in schema:
        f = field.lower()

        if f == "id" or f.endswith("_id") or "employee_id" in f or "account_id" in f:
            type_map[field] = "VARCHAR(32)"
        elif "salary" in f or "price" in f:
            type_map[field] = "DECIMAL(10,2)"
        elif "created_at" in f or "last_login" in f or "joining_date" in f or "deadline" in f or "timestamp" in f:
            type_map[field] = "TIMESTAMP"
        elif "is_active" in f or "mfa_enabled" in f:
            type_map[field] = "BOOLEAN"
        elif "db_port" in f or "stock" in f:
            type_map[field] = "INT"
        else:
            type_map[field] = "VARCHAR(255)"

    return type_map


def sql_literal(value):
    if value is None:
        return "NULL"

    value_str = str(value)

    if value_str.lower() in {"true", "false"}:
        return value_str.upper()

    if value_str.replace(".", "", 1).isdigit():
        return value_str

    escaped = value_str.replace("'", "''")
    return f"'{escaped}'"


# ----------------------------
# COHERENT PROFILE BUILDERS
# ----------------------------

def random_name():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def build_employee_pool(row_count, context):
    """
    Build coherent employee/person profiles.
    Each row has internally consistent fields.
    IDs remain sequential and deterministic per row.
    """
    rows = []
    used_names = set()

    for i in range(row_count):
        name = random_name()

        # reduce excessive duplicates
        attempts = 0
        while name in used_names and attempts < 10:
            name = random_name()
            attempts += 1

        if name in used_names:
            name = f"{name} {i}"

        used_names.add(name)

        department = random.choice(context["departments"])
        role = random.choice(ROLE_MAP.get(department, ["Analyst"]))
        username = name.lower().replace(" ", ".")
        email = random_email(name, context["email_domains"])

        rows.append({
            "employee_id": f"E{100 + i}",
            "user_id": f"USR{1000 + i}",
            "admin_id": f"ADM{500 + i}",
            "customer_id": f"CUST{2000 + i}",
            "vendor_id": f"VND{3000 + i}",
            "project_id": f"PRJ{4000 + i}",
            "system_id": f"SYS{5000 + i}",

            "name": name,
            "full_name": name,
            "username": username,
            "email": email,
            "department": department,
            "role": role,
            "phone": random_phone(),

            "salary": salary_by_department(department),
            "bank_account": random_bank_account(),
            "account_number": random_bank_account(),
            "account_no": random_bank_account(),
            "account_id": random_account_id(),
            "tax_id": random_pan(),

            "bank_name": random.choice(BANKS),
            "ifsc": random_ifsc(),
            "payment_status": random.choice(["Paid", "Pending", "On Hold", "Scheduled"]),

            "password": random_password("high"),
            "password_hash": "$2b$12$J8fY7mJxvD8xT2QxL7x9Ue4QKpA8zq1Y2eM1nO7tR6sW9uB3cD4eF",
            "last_login": random_date(45),
            "is_active": random.choice(["true", "true", "true", "false"]),
            "mfa_enabled": random.choice(["true", "true", "false"]),

            "service_name": random.choice([
                "internal_sync_service",
                "payroll_exporter",
                "vendor_recon_engine"
            ]),
            "integration_name": random.choice([
                "sap_connector",
                "hrms_bridge",
                "vendor_gateway"
            ]),
            "access_key": random_aws_access_key(),
            "secret_key": f"sk_internal_{random.randint(10000000,99999999)}",
            "api_key": f"sk_live_{random.randint(10000000,99999999)}",
            "api_secret": f"sk_secret_{random.randint(10000000,99999999)}",

            "db_name": f"{random.choice(context['project_names']).lower()}_db",
            "db_user": random.choice([
                "finance_admin", "svc_backup", "internal_user", "ops_admin"
            ]),
            "db_password": random_password("high"),
            "db_host": random_ip(),
            "db_port": "5432",
            "environment": "production",

            "hostname": random_host(),
            "ip_address": random_ip(),
            "owner_team": random.choice([
                "ops.team", "finance.ops", "infra.sec", "audit.group"
            ]),
            "owner": random.choice([
                "ops.team", "finance.ops", "infra.sec", "audit.group"
            ]),

            "project_name": random.choice(context["project_names"]),
            "subject": random.choice([
                "Quarterly payroll reconciliation",
                "Vendor payment exception",
                "Access review reminder",
                "Internal audit follow-up"
            ]),
            "priority": random.choice(["low", "medium", "high"]),
            "category": random.choice(["internal", "audit", "ops", "finance"]),
            "price": random.randint(499, 9999),
            "stock": random.randint(5, 150),
            "location": random.choice(["HQ-Storage-A", "DC-Rack-14", "Archive-Room-2"]),
            "status": random.choice(["active", "pending", "reviewed", "approved"]),
            "created_at": random_date(365),
            "joining_date": random_date(900),
            "deadline": random_date(120),
            "timestamp": random_date(30),
            "message": f"Action completed for {name}",
            "level": random.choice(LOG_LEVELS),
            "kyc_status": random.choice(["verified", "pending", "manual_review"])
        })

    return rows

# ----------------------------
# VALUE RESOLUTION
# ----------------------------

def generate_field_value(col, person, i, metadata, context):
    col_lower = col.lower()

    # Always use row data first
    if col in person:
        return person[col]

    for key in person:
        if key.lower() == col_lower:
            return person[key]

    # Strong ID fallback
    if col_lower == "employee_id":
        return f"E{100 + i}"
    elif col_lower == "user_id":
        return f"USR{1000 + i}"
    elif col_lower == "admin_id":
        return f"ADM{500 + i}"
    elif col_lower == "customer_id":
        return f"CUST{2000 + i}"
    elif col_lower == "vendor_id":
        return f"VND{3000 + i}"
    elif col_lower == "project_id":
        return f"PRJ{4000 + i}"
    elif col_lower == "system_id":
        return f"SYS{5000 + i}"
    elif col_lower == "id":
        return f"ID{1000 + i}"
    elif "vendor_name" in col_lower:
        return f"Vendor_{i+1}"

    elif "bank_name" in col_lower:
        return random.choice(BANKS)

    elif "ifsc" in col_lower:
        return random_ifsc()

    elif "payment_status" in col_lower:
        return random.choice(["Paid", "Pending", "On Hold", "Scheduled"])

    elif "password_hash" in col_lower:
        return "$2b$12$examplehashedvalue"

    elif "timestamp" in col_lower or "created_at" in col_lower:
        return random_date()

    elif "level" in col_lower:
        return random.choice(LOG_LEVELS)

    elif "message" in col_lower:
        return f"Action completed for {person['name']}"

    elif "status" in col_lower:
        return random.choice(["active", "pending", "reviewed", "approved"])

    elif "access_key" in col_lower:
        return random_aws_access_key()

    elif "secret_key" in col_lower or "api_secret" in col_lower:
        return f"sk_internal_{random.randint(10000000,99999999)}"

    elif "api_key" in col_lower:
        return f"sk_live_{random.randint(10000000,99999999)}"

    elif "db_host" in col_lower:
        return random_ip()

    elif "db_port" in col_lower:
        return "5432"

    elif "db_name" in col_lower:
        return f"{random.choice(context['project_names']).lower()}_db"

    elif "db_user" in col_lower:
        return random.choice(["finance_admin", "svc_backup", "internal_user", "ops_admin"])

    elif "db_password" in col_lower:
        return random_password("high")

    elif "environment" in col_lower or col_lower == "app_env":
        return "production"

    elif "hostname" in col_lower:
        return random_host()

    elif "ip_address" in col_lower:
        return random_ip()

    elif "owner" in col_lower or "owner_team" in col_lower:
        return random.choice(["ops.team", "finance.ops", "infra.sec", "audit.group"])

    elif "service_name" in col_lower or "integration_name" in col_lower:
        return random.choice(["internal_sync_service", "payroll_exporter", "vendor_recon_engine"])

    elif "kyc_status" in col_lower:
        return random.choice(["verified", "pending", "manual_review"])

    elif "subject" in col_lower:
        return random.choice([
            "Quarterly payroll reconciliation",
            "Vendor payment exception",
            "Access review reminder",
            "Internal audit follow-up"
        ])

    elif "priority" in col_lower:
        return random.choice(["low", "medium", "high"])

    elif "category" in col_lower:
        return random.choice(["internal", "audit", "ops", "finance"])

    elif "price" in col_lower:
        return random.randint(499, 9999)

    elif "stock" in col_lower:
        return random.randint(5, 150)

    elif "location" in col_lower:
        return random.choice(["HQ-Storage-A", "DC-Rack-14", "Archive-Room-2"])

    return f"value_{i+1}"

# ----------------------------
# ENV GENERATION
# ----------------------------

def generate_env_file(metadata):
    context = load_global_context()
    sensitivity = metadata.get("sensitivity", "medium").lower()

    chosen_project = random.choice(context["project_names"]).lower()
    chosen_employee = random_name().lower().replace(" ", ".")
    db_user = random.choice(["finance_admin", "svc_backup", "internal_user", "ops_admin"])
    db_pass = random_password(sensitivity)
    jwt_secret = f"jwt_{random.randint(100000,999999)}_{chosen_project}"
    api_key = f"sk_live_{random.randint(10000000,99999999)}"
    aws_key = random_aws_access_key()

    lines = [
        "APP_ENV=production",
        f"APP_NAME={chosen_project}_service",
        f"DB_HOST={random_ip()}",
        "DB_PORT=5432",
        f"DB_NAME={chosen_project}_db",
        f"DB_USER={db_user}",
        f"DB_PASSWORD={db_pass}",
        f"JWT_SECRET={jwt_secret}",
        f"API_KEY={api_key}",
        f"AWS_ACCESS_KEY_ID={aws_key}",
        f"SERVICE_OWNER={chosen_employee}",
        "DEBUG=false"
    ]

    if sensitivity == "high":
        lines.extend([
            f"REDIS_HOST={random_ip()}",
            f"SMTP_USER=alerts@{random.choice(context['email_domains'])}",
            f"SMTP_PASSWORD={random_password('high')}"
        ])

    return "\n".join(lines)


# ----------------------------
# CSV GENERATION
# ----------------------------

def generate_csv(schema, metadata):
    context = load_global_context()
    schema = maybe_enrich_schema(schema, metadata)
    size_bytes = parse_size_to_bytes(metadata.get("size", "25kb"))
    row_count = estimate_row_count(size_bytes, "csv", len(schema))
    employee_pool = build_employee_pool(row_count, context)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(schema)

    for i, person in enumerate(employee_pool):
        row = [generate_field_value(col, person, i, metadata, context) for col in schema]
        writer.writerow(row)

    return output.getvalue().strip()


# ----------------------------
# JSON GENERATION
# ----------------------------

def generate_json(schema, metadata):
    print("DEBUG: NEW generate_json IS RUNNING")
    context = load_global_context()
    schema = maybe_enrich_schema(schema, metadata)

    size_bytes = parse_size_to_bytes(metadata.get("size", "25kb"))
    row_count = estimate_row_count(size_bytes, "json", len(schema))
    employee_pool = build_employee_pool(row_count, context)

    print("DEBUG FIRST PERSON:", employee_pool[0])

    data = []

    for i, person in enumerate(employee_pool):
        item = {}
        for col in schema:
            item[col] = generate_field_value(col, person, i, metadata, context)
        data.append(item)

    print("DEBUG FIRST JSON ITEM:", data[0])

    return json.dumps(data, indent=4)
# ----------------------------
# SQL GENERATION
# ----------------------------

def generate_sql(path, schema, metadata):
    context = load_global_context()
    schema = maybe_enrich_schema(schema, metadata)
    size_bytes = parse_size_to_bytes(metadata.get("size", "25kb"))
    row_count = estimate_row_count(size_bytes, "sql", len(schema))
    employee_pool = build_employee_pool(row_count, context)

    table_name = infer_table_name(path, metadata)
    safe_schema = [sanitize_sql_identifier(col) for col in schema]
    sql_types = infer_sql_types(safe_schema)

    create_stmt = f"CREATE TABLE {table_name} (\n"
    create_stmt += ",\n".join(
        [f"    {col} {sql_types.get(col, 'VARCHAR(255)')}" for col in safe_schema]
    )
    create_stmt += "\n);\n\n"

    inserts = []
    for i, person in enumerate(employee_pool):
        values = [
            sql_literal(generate_field_value(orig_col, person, i, metadata, context))
            for orig_col in schema
        ]
        inserts.append(
            f"INSERT INTO {table_name} ({', '.join(safe_schema)}) VALUES ({', '.join(values)});"
        )

    return create_stmt + "\n".join(inserts)


# ----------------------------
# CREDENTIAL FILE GENERATION
# ----------------------------

def generate_credentials(metadata):
    context = load_global_context()
    sensitivity = metadata.get("sensitivity", "medium").lower()
    size_bytes = parse_size_to_bytes(metadata.get("size", "5kb"))
    row_count = min(300, estimate_row_count(size_bytes, "txt", 3))

    profiles = build_employee_pool(row_count, context)

    lines = []
    for person in profiles:
        username = person["username"]
        role = person["role"]
        password = random_password(sensitivity)
        lines.append(f"{username} : {password} ({role})")

    return "\n".join(lines)


# ----------------------------
# LOG FILE GENERATION
# ----------------------------

def generate_logs(metadata):
    print("🔥 REAL generate_logs EXECUTED")
    context = load_global_context()
    size_bytes = parse_size_to_bytes(metadata.get("size", "15kb"))
    row_count = min(5000, estimate_row_count(size_bytes, "log", 4))

    lines = []
    for _ in range(row_count):
        ts = random_date()
        level = random.choice(LOG_LEVELS)
        user = random_name().lower().replace(" ", ".")
        action = random.choice(LOG_ACTIONS)
        project = random.choice(context["project_names"])

        line = f"[{ts}] [{level}] User={user} Event={action} Project={project}"

        if random.random() < 0.35:
            line += f" Session={random.randint(1000,9999)}"

        if random.random() < 0.25:
            line += f" Host={random_host()}"

        lines.append(line)

    return "\n".join(lines)


# ----------------------------
# NOTE / TXT FILE GENERATION
# ----------------------------

def generate_text_note(metadata):
    context = load_global_context()
    sensitivity = metadata.get("sensitivity", "medium").lower()

    notes = [
        f"Quarterly review pending for project {random.choice(context['project_names'])}.",
        "Vendor reconciliation sheet needs update before external audit.",
        "Payroll review flagged 2 pending approvals from Finance.",
        "Do not share contractor list outside internal mail.",
        "Backup credentials rotated last cycle. Confirm access with admin team.",
        f"Escalate budget variance issue to {random_name()}.",
        "Pending access review for privileged internal folders.",
        "Compliance sign-off required before monthly archival export."
    ]

    if sensitivity == "high":
        notes.extend([
            "Temporary admin access granted for finance migration window.",
            "Credential rotation deferred pending vendor API dependency review."
        ])

    sample_count = min(max(3, len(notes) // 2), 6)
    return "\n".join(random.sample(notes, sample_count))


# ----------------------------
# MAIN ENTRY FUNCTION
# ----------------------------

def generate(path, metadata, schema):
    file_type = metadata.get("file_type", "").lower()
    content_type = metadata.get("content_type", "").lower()

    if file_type == "csv":
        return generate_csv(schema, metadata)

    elif file_type == "json":
        return generate_json(schema, metadata)

    elif file_type == "sql":
        return generate_sql(path, schema, metadata)

    elif file_type == "env":
        return generate_env_file(metadata)

    elif file_type == "txt":
        if content_type == "credentials":
            return generate_credentials(metadata)
        elif content_type == "logs":
            return generate_logs(metadata)
        elif content_type == "env":
            return generate_env_file(metadata)
        else:
            return generate_text_note(metadata)

    elif file_type == "log":
        return generate_logs(metadata)

    return generate_text_note(metadata)