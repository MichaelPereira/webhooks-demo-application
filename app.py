from flask import Flask, render_template, request

import logging
import os
import requests

# Flask application and global variable initialization.
app = Flask(__name__)
# logging.setLevel(logging.NOTSET)
@app.route("/")
def hello():
    return 'Hello World!'

def is_ping_event(request):
    """
    Check if the current request is a ping event
    """
    return request.headers.get('X-GitHub-Event') == 'ping'

@app.route('/gitlab_event', methods=['POST'])
def repo_created():
    """
    Hook for creating a jenkins job automatically,
    along with the hook to send push event automatically
    and also optionally send a slack notification about
    the creation of that repository
    """
    data = request.json or request.form
    logging.warning(data)
    return str(data), 200

# Part of the Flask Application that runs a development websever
# Please don't this as-is in production :)
if __name__ == "__main__":
    app.run(host= '0.0.0.0')

