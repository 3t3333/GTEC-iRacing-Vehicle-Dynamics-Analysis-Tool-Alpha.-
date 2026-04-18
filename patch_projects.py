with open('analysis/projects.py', 'r') as f:
    content = f.read()

content = content.replace(
    'print("  2. Open Existing Project")',
    'print("  2. Open Existing Project")\n        print("  3. Manage Workbooks")'
)

content = content.replace(
    "elif choice == '2':\n            list_projects()",
    "elif choice == '2':\n            list_projects()\n        elif choice == '3':\n            from analysis.workflow_engine import manage_workbooks\n            manage_workbooks()"
)

content = content.replace(
    "from analysis.workflow_engine import run_standard_workflow\n            latest = state['linked_files'][-1] if state['linked_files'] else None\n            baseline = state['baseline']\n            if latest:\n                run_standard_workflow(name, latest, baseline)\n            else:\n                print(\"[!] No files linked to this project.\")",
    "from analysis.workflow_engine import execute_workflow\n            execute_workflow(name, state)"
)

with open('analysis/projects.py', 'w') as f:
    f.write(content)
