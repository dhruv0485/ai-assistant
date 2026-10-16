"""
seed_templates.py (DISABLED)

NOTE: The 130 templates in jd_templates.json are candidate benchmark reference roles
for /check-score only. They must NEVER be seeded as job postings into the Supabase 'jobs' table.
The HR Dashboard and Candidate Openings boards are strictly reserved for real jobs created by HR.
"""

import sys

def main():
    print("[HYT Safety Notice] Benchmark templates must NOT be seeded as job postings into Supabase.")
    print("The 130 templates in jd_templates.json are strictly used by /check-score as benchmark reference criteria.")
    sys.exit(0)

if __name__ == "__main__":
    main()
