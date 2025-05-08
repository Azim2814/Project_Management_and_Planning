import docx
import re
import os
from jira import JIRA
from github import Github
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

# --- Load Flan-T5 model ---
model_name = "google/flan-t5-large"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
flan_pipeline = pipeline("text2text-generation", model=model, tokenizer=tokenizer)

# --- Authentication ---
from dotenv import load_dotenv
load_dotenv()
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
JIRA_URL = 'https://azimnathani806.atlassian.net'
JIRA_EMAIL ='azimnathani806@gmail.com'
GITHUB_REPO = 'Azim2814/Project_automation'
PROJECT_KEY = 'APM'

jira = JIRA(server=JIRA_URL, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))
g = Github(GITHUB_TOKEN)
repo = g.get_repo(GITHUB_REPO)

# --- Read Word Document ---
def extract_stories_from_docx(docx_path):
    doc = docx.Document(docx_path)
    stories = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            stories.append(text)
    return stories

# --- Generate test cases using Flan-T5 ---
def generate_test_cases_flan(text: str, max_length=256, num_return_sequences=1):
    prompt = f"Generate software test cases for the following requirement:\n{text.strip()}"
    result = flan_pipeline(prompt, max_length=max_length, num_return_sequences=num_return_sequences, do_sample=False)
    return result[0]['generated_text'].strip()

# --- Create Jira ticket ---
def create_jira_ticket(ticket_summary, ticket_description, test_case):
    ticket_summary = ticket_summary.replace('\n', ' ')

    # Check for duplicate Jira tickets
    existing_issues = jira.search_issues(f'project={PROJECT_KEY} AND summary ~ "{ticket_summary}"')
    if existing_issues:
        print(f"⚠️ Jira ticket already exists: {existing_issues[0].key}")
        return existing_issues[0].key

    description_with_tests = f"{ticket_description}\n\n### Test Cases\n{test_case}"


    issue_dict = {
        'project': {'key': PROJECT_KEY},
        'summary': ticket_summary,
        'description': description_with_tests,
        'issuetype': {'name': 'Task'},
    }

    issue = jira.create_issue(fields=issue_dict)
    print(f"✅ Jira ticket created: {issue.key}")
    return issue.key

# --- Create GitHub branch ---
def create_branch_and_readme(branch_name, summary):
    existing_branches = [b.name for b in repo.get_branches()]
    if branch_name in existing_branches:
        print(f"⚠️ Branch already exists: {branch_name}")
        return

    source = repo.get_branch("main")
    repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=source.commit.sha)
    print(f"✅ GitHub branch created: {branch_name}")

    readme_content = f"# {branch_name}\n\n{summary}"
    try:
        repo.create_file(f"{branch_name}_README.md", f"Add README for {branch_name}", readme_content, branch=branch_name)
        print(f"✅ README committed to {branch_name}")
    except Exception as e:
        print(f"❌ Failed to commit README: {e}")
# --- Main pipeline ---
def main():
    print("📄 Reading requirements.docx...")
    stories = extract_stories_from_docx("requirements.docx")
    print("\n✅ Extracted Stories:")
    for story in stories:
        print(f"- {story}")

    print("\n🚀 Creating Jira + GitHub setup...")
    for story in stories:
        ticket_summary = story if len(story) < 100 else story[:97] + "..."
        ticket_description = story
        print(f"\n🧪 Generating test case for: {ticket_summary}")
        test_case = generate_test_cases_flan(ticket_description)

        issue_key = create_jira_ticket(ticket_summary, ticket_description, test_case)
        create_branch_and_readme(issue_key, ticket_summary)

        print(f"\n🔖 {issue_key} processed.\n")

    print("\n🎯 All stories processed.")

if __name__ == "__main__":
    main()

