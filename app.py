from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from github import Github, GithubException
from string import Template
from slacker import Slacker
from sqlalchemy.dialects.mysql import INTEGER, MEDIUMTEXT, DATETIME

import logging
import os
import requests

# Flask application and global variable initialization.
app = Flask(__name__)
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
SLACK_TOKEN = os.environ.get('SLACK_TOKEN', '')
MYSQL_USER = os.environ.get('MYSQL_USER')
MYSQL_HOST = os.environ.get('MYSQL_HOST')
MYSQL_DB = os.environ.get('MYSQL_DATABASE')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://{user}:{password}@{host}/{db}'.format(**{
        'user': MYSQL_USER,
        'password': MYSQL_PASSWORD,
        'host': MYSQL_HOST,
        'db': MYSQL_DB,
    })
db = SQLAlchemy(app)

@app.route("/")
def hello():
    return 'Hello World!'

def is_ping_event(request):
    """
    Check if the current request is a ping event
    """
    return request.headers.get('X-GitHub-Event') == 'ping'

@app.route('/repo_created', methods=['POST'])
def github_hook():
    """
    Hook for creating a jenkins job automatically,
    along with the hook to send push event automatically
    and also optionally send a slack notification about
    the creation of that repository
    """
    data = request.json or request.form
    if is_ping_event(request):
        return data['zen'], 200

    if data['action'] == 'created':
        repo_full_name = data['repository']['full_name']
        repo_short_name = data['repository']['name']
        username = data['sender']['login']
        g = Github(GITHUB_TOKEN)

        repo = g.get_repo(repo_full_name)
        # Replace the organization below with yours
        org = g.get_organization('devopsqanj')

        add_jenkins_hook(repo)
        create_jenkins_job(repo_short_name)
        if SLACK_TOKEN:
            # Only send a notification if there is a slack token set
            send_slack_notification(org, repo_short_name, username)

        return 'new repository successfully configured', 200


def send_slack_notification(org, repo_short_name, username):
    """
    Send a slack notification that the repository was created
    and display the number of public repos of the organization.
    For a real organization, you should display the number of
    private repositories
    :param org: The github organization object from pygithub
    :param repo_short_name: The name of the repository as a String
    :param username: The name of the user who created the repository
    """
    slack = Slacker(SLACK_TOKEN)
    msg = '%s repository created by %s. %d public repositories' \
          % (repo_short_name, username, org.public_repos)
    slack.chat.post_message(channel='#channel-name', text=msg)


@app.route('/api/github_org_member_hook', methods=['POST'])
def github_org_member_hook():
    """
    Hook for organization events. When a user is added or removed from the org,
    add/remove them from users.txt in the people repo
    """
    data = request.json or request.form
    if is_ping_event(request):
        return data['zen'], 200
    if data['action'] in ['member_added', 'member_removed']:
        sponsor = data['sender']['login']
        member = data['membership']['user']['login']
        action = data['action'].split('_')[1]

        try:
            g = Github(GITHUB_TOKEN)
            people_repo = g.get_repo('DevOpsQANJ/people')
            user_file = people_repo.get_file_contents('users.txt')
            user_list = user_file.decoded_content.strip().split('\n')
            list_updated = False

            if action == 'added' and member not in user_list:
                user_list.append(member)
                list_updated = True
            elif action == 'removed' and member in user_list:
                user_list.remove(member)
                list_updated = True

            if list_updated:
                people_repo.update_file('/users.txt',
                                        message='%s %s by %s' % (member, action, sponsor),
                                        content='\n'.join(sorted(user_list)),
                                        sha=user_file.sha,
                                        branch='master')
                return 'user successfully %s' % action, 200
        except GithubException as e:
            return 'an error occurred with github: %s' % str(e), 500
    return '', 200

def create_jenkins_job(repo_short_name):
    """
    This function creates a jenkins job by uploading this big XML
    blob that only has the repo name (which will be the job name)
    configurable. You would have to recreate that from the file downloaded at
    http://localhost:8080/<job_name>/config.xml
    so that it would contain the correct credentials id and organization name for
    your case
    """
    template = Template("""<?xml version='1.0' encoding='UTF-8'?>
<org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject plugin="workflow-multibranch@2.14">
  <actions/>
  <description></description>
  <properties>
    <org.jenkinsci.plugins.pipeline.modeldefinition.config.FolderConfig plugin="pipeline-model-definition@1.1.1">
      <dockerLabel></dockerLabel>
      <registry plugin="docker-commons@1.6"/>
    </org.jenkinsci.plugins.pipeline.modeldefinition.config.FolderConfig>
  </properties>
  <folderViews class="jenkins.branch.MultiBranchProjectViewHolder" plugin="branch-api@2.0.8">
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </folderViews>
  <healthMetrics>
    <com.cloudbees.hudson.plugins.folder.health.WorstChildHealthMetric plugin="cloudbees-folder@6.0.3">
      <nonRecursive>false</nonRecursive>
    </com.cloudbees.hudson.plugins.folder.health.WorstChildHealthMetric>
  </healthMetrics>
  <icon class="jenkins.branch.MetadataActionFolderIcon" plugin="branch-api@2.0.8">
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </icon>
  <orphanedItemStrategy class="com.cloudbees.hudson.plugins.folder.computed.DefaultOrphanedItemStrategy" plugin="cloudbees-folder@6.0.3">
    <pruneDeadBranches>true</pruneDeadBranches>
    <daysToKeep>0</daysToKeep>
    <numToKeep>0</numToKeep>
  </orphanedItemStrategy>
  <triggers/>
  <sources class="jenkins.branch.MultiBranchProject$BranchSourceList" plugin="branch-api@2.0.8">
    <data>
      <jenkins.branch.BranchSource>
        <source class="org.jenkinsci.plugins.github_branch_source.GitHubSCMSource" plugin="github-branch-source@2.0.4">
          <id>010efe08-e229-468d-bde4-d21a770b996d</id>
          <checkoutCredentialsId>SAME</checkoutCredentialsId>
          <scanCredentialsId>e713e969-8c86-44a9-b761-99332a16f42c</scanCredentialsId>
          <repoOwner>devopsqanj</repoOwner>
          <repository>$repo_short_name</repository>
          <includes>*</includes>
          <excludes></excludes>
          <buildOriginBranch>true</buildOriginBranch>
          <buildOriginBranchWithPR>true</buildOriginBranchWithPR>
          <buildOriginPRMerge>false</buildOriginPRMerge>
          <buildOriginPRHead>false</buildOriginPRHead>
          <buildForkPRMerge>true</buildForkPRMerge>
          <buildForkPRHead>false</buildForkPRHead>
        </source>
        <strategy class="jenkins.branch.DefaultBranchPropertyStrategy">
          <properties class="empty-list"/>
        </strategy>
      </jenkins.branch.BranchSource>
    </data>
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </sources>
  <factory class="org.jenkinsci.plugins.workflow.multibranch.WorkflowBranchProjectFactory">
    <owner class="org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject" reference="../.."/>
  </factory>
</org.jenkinsci.plugins.workflow.multibranch.WorkflowMultiBranchProject>

    """)
    job_xml = template.safe_substitute({'repo_short_name': repo_short_name})
    jenkins_create_item_url = 'http://admin:admin@jenkins:8080/createItem?name=%s' \
                                % repo_short_name

    headers = {'Content-Type': 'application/xml'}

    response = requests.post(jenkins_create_item_url, headers=headers, data=job_xml)
    print response.text


def add_jenkins_hook(repo):
    """
    Automatically create the github webhook configuration that will notify the
    jenkins job every time a commit is being pushed to the github repository
    :param repo: repository object obtained from pygithub
    """
    hook_config = dict(url='http://b8180a88.ngrok.io/github-webhook/', content_type='json')
    subscribed_events = ['push']
    try:
        repo.create_hook(name='web', config=hook_config, events=subscribed_events, active=True)
    except GithubException as e:
        logging.error(str(e))


class Event(db.Model):
    """
    This class just does the mapping to a database table, to
    easily translate python objects into DB entities.
    """
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(80))
    event_content = db.Column(MEDIUMTEXT)


@app.route('/store_events', methods=['POST'])
def store_events():
    """
    This endpoint stores all events sent by github into a single table
    """
    data = request.json or request.form
    if is_ping_event(request):
        return data['zen'], 200
    ev = Event()
    ev.event_name = request.headers.get('X-GitHub-Event')
    ev.event_content = str(data)
    db.session.add(ev)
    db.session.commit()
    return 'event stored', 200


@app.route('/search_secrets', methods=['POST'])
def search_secrets():
    """
    This endpoint searches for secret in a commit,
    you should either load:
    - real secrets from secure locations like Hashicorp
      or Ansible Vault,
    - search for things that look like secrets with regex
      or dedicated tools like https://github.com/dxa4481/truffleHog
    """
    data = request.json or request.form
    if is_ping_event(request):
        return data['zen'], 200

    new_sha = data['after']
    old_sha = data['before']
    author = data['head_commit']['author']['username']
    repo_full_name = data['repository']['full_name']
    g = Github(GITHUB_TOKEN)

    repo = g.get_repo(repo_full_name)
    comparison = repo.compare(old_sha, new_sha)
    for modified_file in comparison.files:
        if 'mysecret' in modified_file.patch:

            title = 'Commit contains secrets'
            body = """Your commit contains some secrets that are not supposed to be in the code.
                    Details below:

                    %s.

                    PLEASE REVIEW THE COMMIT AND TAKE APPROPRIATE ACTION.
                    """ % 'found mysecret'
            repo.create_issue(title, body=body, assignee=author, labels=['FoundSecret'])
        return 'issue created', 200
    return 'no issue found', 200

# Part of the Flask Application that runs a development websever
# Please don't this as-is in production :)
db.create_all()
if __name__ == "__main__":
    app.run(host= '0.0.0.0')

