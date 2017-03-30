# webhooks-demo-application

This is a demo application of github Webhooks consumption setup as little
Flask application with a few endpoints exposed and ready to process a few github webhooks.

Requirements
------------
The only requirements is to have `docker`and `docker-compose` since this is how the stack runs. The rest of the application is being run as docker containers, so you don't need to install and configure anything to run it.
At the end, you can delete all the images and volumes created with:

    $ docker system prune

Testing locally with ngrok
--------------------------
Since github needs to send the events to a publicly accessible URL and
all the services are running locally on a laptop, we have to use something
to make the connection between the two. In this case, the best tool is [ngrok](https://ngrok.com/).

For the purpose of this application, as the demo service is running on port 80 and jenkins on port 8080, we need the `ngrok` command twice in two different terminals:

    $ ./ngrok http 80
    $ ./ngrok http 8080

These two commands will show two ngrok URLs in the form of `http://bb1c23b4.ngrok.io`. This is what you should put as prefix to each webhook endpoint to allow github to send the events directly to the local application.

Example Endpoints
-----------------
- `/repo_created`

This endpoint should be set as an organization webhook configured to
receive [repositories events](https://developer.github.com/v3/activity/events/types/#repositoryevent).

It will create a jenkins job on the jenkins service running on
[http://localhost:8080](http://localhost:8080) everytime a github
repository is created, and create the repo webhook that will allow the
jenkins job to receive commit events to know when to build them.

- `/github_org_member_hook`

This endpoint should set as an organization webhook configured to receive [organization events](https://developer.github.com/v3/activity/events/types/#organizationevent).

It will automatically add any person who accept the invitation to join the organizaation to the `users.txt` file in the `people` repository, along with the information of who invited them into the organization.
This is best used in conjuction with [gu-who](https://github.com/guardian/gu-who)
to automate one of the github account requirements.

- `/store_events`

This endpoint should be set as an organization webhook configured to receive [all events](https://developer.github.com/webhooks/#wildcard-event).

It will automatically store all events from the whole organization into a
database with a single table, for later querying/processing. For a real
application, more processing would be done to store the events in a
format that make it easier to query.

- `/search_secrets`

This endpoint should be set as an organization webhook configured to receive [push events](https://developer.github.com/v3/activity/events/types/#pushevent).

It will look for _secrets_ in all github commits pushed in the organization. The goal is to catch any secrets exposed in the code and act on them by sending a notification and even deprecating them if possible. The current implement is hard-coded, you should either:

- - real secrets from secure locations like [Hashicorp Vault](https://www.vaultproject.io/)
      or [Ansible Vault](http://docs.ansible.com/ansible/playbooks_vault.html),
- - search for things that look like secrets with regexes
      or dedicated tools like [truffleHog](https://github.com/dxa4481/truffleHog)