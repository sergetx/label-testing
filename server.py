import os
import io
import lxml
import time
import shutil
import flask
import pandas as pd
import logging
import logging.config
import traceback as tb
import label_studio

try:
    import ujson as json
except:
    import json

# setup default config
with io.open(os.path.join(os.path.dirname(__file__), 'logger.json')) as f:
    logging.config.dictConfig(json.load(f))

from uuid import uuid4
from urllib.parse import unquote
from datetime import datetime
from inspect import currentframe, getframeinfo
from flask import (
    request, jsonify, make_response, Response, Response as HttpResponse, send_file, session, redirect
)
from flask_api import status
from types import SimpleNamespace

from label_studio.utils.functions import generate_sample_task
from label_studio.utils.io import find_dir, find_editor_files
from label_studio.utils import uploader
from label_studio.utils.validation import TaskValidator
from label_studio.utils.exceptions import ValidationError
from label_studio.utils.functions import generate_sample_task_without_check
from label_studio.utils.misc import (
    exception_treatment, exception_treatment_page,
    config_line_stripped, get_config_templates, convert_string_to_hash, serialize_class
)
from label_studio.utils.argparser import parse_input_args
from label_studio.utils.uri_resolver import resolve_task_data_uri
from label_studio.storage import get_storage_form

from label_studio.project import Project
from label_studio.tasks import Tasks

logger = logging.getLogger(__name__)

app = flask.Flask(__name__, static_url_path='')

app.secret_key = 'A0Zrdqwf1AQWj12ajkhgFN]dddd/,?RfDWQQT'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['WTF_CSRF_ENABLED'] = False

# input arguments
input_args = None
if os.path.exists('server.json'):
    try:
        with open('server.json') as f:
            input_args = SimpleNamespace(**json.load(f))
    except:
        pass


def project_get_or_create(multi_session_force_recreate=False):
    """
    Return existed or create new project based on environment. Currently supported methods:
    - "fixed": project is based on "project_name" attribute specified by input args when app starts
    - "session": project is based on "project_name" key restored from flask.session object
    :return:
    """
    if input_args.command == 'start-multi-session':
        # get user from session
        if 'user' not in session:
            session['user'] = str(uuid4())
        user = session['user']

        # get project from session
        if 'project' not in session or multi_session_force_recreate:
            session['project'] = str(uuid4())
        project = session['project']

        project_name = user + '/' + project
        return Project.get_or_create(project_name, input_args, context={
            'multi_session': True,
            'user': convert_string_to_hash(user)
        })
    else:
        if multi_session_force_recreate:
            raise NotImplementedError(
                '"multi_session_force_recreate" option supported only with "start-multi-session" mode')
        return Project.get_or_create(input_args.project_name, input_args, context={'multi_session': False})


@app.template_filter('json')
def json_filter(s):
    return json.dumps(s)


@app.before_first_request
def app_init():
    pass


@app.route('/static/media/<path:path>')
def send_media(path):
    """ Static for label tool js and css
    """
    media_dir = find_dir('static/media')
    return flask.send_from_directory(media_dir, path)


@app.route('/upload/<path:path>')
def send_upload(path):
    """ User uploaded files
    """
    project = project_get_or_create()
    project_dir = os.path.join(project.name, 'upload')
    print(project_dir, path)
    return open(os.path.join(project_dir, path), 'rb').read()


@app.route('/static/<path:path>')
def send_static(path):
    """ Static serving
    """
    static_dir = find_dir('static')
    return flask.send_from_directory(static_dir, path)


@app.errorhandler(ValidationError)
def validation_error_handler(error):
    logger.error(error)
    return str(error), 500


@app.route('/')
@exception_treatment_page
def labeling_page():
    """ Label studio frontend: task labeling
    """
    project = project_get_or_create()
    if project.no_tasks():
        return redirect('/welcome')

    # task data: load task or task with completions if it exists
    task_data = None
    task_id = request.args.get('task_id', None)

    if task_id is not None:
        task_id = int(task_id)
        # Task explore mode
        task_data = project.get_task_with_completions(task_id) or project.source_storage.get(task_id)
        task_data = resolve_task_data_uri(task_data)

        if project.ml_backends_connected:
            task_data = project.make_predictions(task_data)

    project.analytics.send(getframeinfo(currentframe()).function)
    return flask.render_template(
        'labeling.html',
        project=project,
        config=project.config,
        label_config_line=project.label_config_line,
        task_id=task_id,
        task_data=task_data,
        **find_editor_files()
    )


@app.route('/welcome')
@exception_treatment_page
def welcome_page():
    """ Label studio frontend: task labeling
    """
    project = project_get_or_create()
    project.analytics.send(getframeinfo(currentframe()).function)
    project.update_on_boarding_state()
    return flask.render_template(
        'welcome.html',
        config=project.config,
        project=project,
        on_boarding=project.on_boarding
    )


@app.route('/tasks', methods=['GET', 'POST'])
@exception_treatment_page
def tasks_page():
    """ Tasks and completions page
    """
    try:
        project = project_get_or_create()
        serialized_project = project.serialize()
        serialized_project['multi_session_mode'] = input_args.command != 'start-multi-session'
        project.analytics.send(getframeinfo(currentframe()).function)
        return flask.render_template(
            'tasks.html',
            project=project,
            serialized_project=serialized_project
        )
    except Exception as e:
        error = str(e)
        traceback = tb.format_exc()
        return flask.render_template(
            'includes/error.html',
            error=error, header="Project loading error", traceback=traceback
        )
import os
import io
import lxml
import time
import shutil
import flask
import pandas as pd
import logging
import logging.config
import traceback as tb

try:
    import ujson as json
except:
    import json

# setup default config
with io.open(os.path.join(os.path.dirname(__file__), 'logger.json')) as f:
    logging.config.dictConfig(json.load(f))

from uuid import uuid4
from urllib.parse import unquote
from datetime import datetime
from inspect import currentframe, getframeinfo
from flask import (
    request, jsonify, make_response, Response, Response as HttpResponse, send_file, session, redirect
)
from flask_api import status
from types import SimpleNamespace

from label_studio.utils.functions import generate_sample_task
from label_studio.utils.io import find_dir, find_editor_files
from label_studio.utils import uploader
from label_studio.utils.validation import TaskValidator
from label_studio.utils.exceptions import ValidationError
from label_studio.utils.functions import generate_sample_task_without_check
from label_studio.utils.misc import (
    exception_treatment, exception_treatment_page,
    config_line_stripped, get_config_templates, convert_string_to_hash, serialize_class
)
from label_studio.utils.argparser import parse_input_args
from label_studio.utils.uri_resolver import resolve_task_data_uri
from label_studio.storage import get_storage_form

from label_studio.project import Project
from label_studio.tasks import Tasks

logger = logging.getLogger(__name__)

app = flask.Flask(__name__, static_url_path='')

app.secret_key = 'A0Zrdqwf1AQWj12ajkhgFN]dddd/,?RfDWQQT'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['WTF_CSRF_ENABLED'] = False

# input arguments
input_args = None
if os.path.exists('server.json'):
    try:
        with open('server.json') as f:
            input_args = SimpleNamespace(**json.load(f))
    except:
        pass


def project_get_or_create(multi_session_force_recreate=False):
    """
    Return existed or create new project based on environment. Currently supported methods:
    - "fixed": project is based on "project_name" attribute specified by input args when app starts
    - "session": project is based on "project_name" key restored from flask.session object
    :return:
    """
    if input_args.command == 'start-multi-session':
        # get user from session
        if 'user' not in session:
            session['user'] = str(uuid4())
        user = session['user']

        # get project from session
        if 'project' not in session or multi_session_force_recreate:
            session['project'] = str(uuid4())
        project = session['project']

        project_name = user + '/' + project
        return Project.get_or_create(project_name, input_args, context={
            'multi_session': True,
            'user': convert_string_to_hash(user)
        })
    else:
        if multi_session_force_recreate:
            raise NotImplementedError(
                '"multi_session_force_recreate" option supported only with "start-multi-session" mode')
        return Project.get_or_create(input_args.project_name, input_args, context={'multi_session': False})


@app.template_filter('json')
def json_filter(s):
    return json.dumps(s)


@app.before_first_request
def app_init():
    pass


@app.route('/static/media/<path:path>')
def send_media(path):
    """ Static for label tool js and css
    """
    media_dir = find_dir('static/media')
    return flask.send_from_directory(media_dir, path)


@app.route('/upload/<path:path>')
def send_upload(path):
    """ User uploaded files
    """
    project = project_get_or_create()
    project_dir = os.path.join(project.name, 'upload')
    print(project_dir, path)
    return open(os.path.join(project_dir, path), 'rb').read()


@app.route('/static/<path:path>')
def send_static(path):
    """ Static serving
    """
    static_dir = find_dir('static')
    return flask.send_from_directory(static_dir, path)


@app.errorhandler(ValidationError)
def validation_error_handler(error):
    logger.error(error)
    return str(error), 500


@app.route('/')
@exception_treatment_page
def labeling_page():
    """ Label studio frontend: task labeling
    """
    project = project_get_or_create()
    if project.no_tasks():
        return redirect('/welcome')

    # task data: load task or task with completions if it exists
    task_data = None
    task_id = request.args.get('task_id', None)

    if task_id is not None:
        task_id = int(task_id)
        # Task explore mode
        task_data = project.get_task_with_completions(task_id) or project.source_storage.get(task_id)
        task_data = resolve_task_data_uri(task_data)

        if project.ml_backends_connected:
            task_data = project.make_predictions(task_data)

    project.analytics.send(getframeinfo(currentframe()).function)
    return flask.render_template(
        'labeling.html',
        project=project,
        config=project.config,
        label_config_line=project.label_config_line,
        task_id=task_id,
        task_data=task_data,
        **find_editor_files()
    )


@app.route('/welcome')
@exception_treatment_page
def welcome_page():
    """ Label studio frontend: task labeling
    """
    project = project_get_or_create()
    project.analytics.send(getframeinfo(currentframe()).function)
    project.update_on_boarding_state()
    return flask.render_template(
        'welcome.html',
        config=project.config,
        project=project,
        on_boarding=project.on_boarding
    )


@app.route('/tasks', methods=['GET', 'POST'])
@exception_treatment_page
def tasks_page():
    """ Tasks and completions page
    """
    try:
        project = project_get_or_create()
        serialized_project = project.serialize()
        serialized_project['multi_session_mode'] = input_args.command != 'start-multi-session'
        project.analytics.send(getframeinfo(currentframe()).function)
        return flask.render_template(
            'tasks.html',
            project=project,
            serialized_project=serialized_project
        )
    except Exception as e:
        error = str(e)
        traceback = tb.format_exc()
        return flask.render_template(
            'includes/error.html',
            error=error, header="Project loading error", traceback=traceback
        )
