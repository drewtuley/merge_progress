from flask import Flask
from flask import render_template
from flask import Markup
from flask import send_from_directory
from flask import request
from flask import redirect, url_for

import os
from datetime import datetime
from MergeProgress import MergeProgress
from MergeProgress import MergeJira
from MergeProgress import Status
from MergeProgress import StateMap


class App(Flask):
    logger = None
    merge_progress = None
    session = None

    def set_logger(self, logger):
        self.logger = logger

    def set_merge_progress(self, merge_progress):
        self.merge_progress = merge_progress

    def set_session(self, session):
        self.session = session


app = App(__name__)

state_class_map = {1: 'pending_dev', 2: 'pending', 3: 'testing', 4: 'merged', 10: 'archived'}


def get_state_mappings(session):
    state_mapping = {}
    state_maps = session.query(StateMap).order_by('state')
    for state_map in state_maps:
        state_mapping[state_map.state] = state_map.description
    return state_mapping


def get_state_class(state):
    return state_class_map[state]


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


def markup_progress_row(jira, state_mapping):
    return render_template('progress_row.html', row_cls=get_state_class(jira.state), id=jira.jid, title=jira.title,
                           mapped_state=state_mapping[jira.state])


@app.route('/progress/', methods=['GET'])
def show_progress():
    session = app.merge_progress.get_db_session()

    state_mapping = get_state_mappings(session)

    jira_list = session.query(MergeJira).order_by('state').order_by('jid').limit(25)

    table = '<table width="100%">'
    for jira in jira_list:
        if jira.state < 10:
            table += markup_progress_row(jira, state_mapping)
    table += '</table>'

    status_map = {}
    statuses = session.query(Status)
    for status in statuses:
        status_map[status.key] = status.value

    return render_template('merge_progress.html', data=Markup(table), date=str(datetime.now()),
                           **status_map);


def markup_list_row(jira, state_mapping):
    return render_template('list_row.html', row_cls=get_state_class(jira.state),
                           mapped_state=state_mapping[jira.state], **jira.get_props())


@app.route('/mgmt/', methods=['GET'])
def do_mgmt():
    return render_template('mgmt.html')


@app.route('/list/', methods=['GET'])
def show_list():
    session = app.merge_progress.get_db_session()
    state_mapping = get_state_mappings(session)

    jira_list = session.query(MergeJira).order_by('state').order_by('jid')

    table = '<table width="100%">'
    for jira in jira_list:
        table += markup_list_row(jira, state_mapping)
    table += '</table>'

    status_map = {}
    statuses = session.query(Status)
    for status in statuses:
        status_map[status.key] = status.value

    return render_template('merge_list.html', data=Markup(table))


def render_state_options(status_map, current_state):
    datalist = ''
    for key in status_map:
        if key == current_state:
            selected = 'selected'
        else:
            selected = ''
        datalist += '<option value="{k}" {s}>{v}</option>'.format(k=key, v=status_map[key], s=selected)
    return datalist


@app.route('/edit/', methods=['GET'])
def do_edit():
    jid = request.args.get('jid')

    session = app.merge_progress.get_db_session()
    jira = session.query(MergeJira).filter_by(jid=jid).first()
    state_mapping = get_state_mappings(session)

    return render_template('edit_page.html', state_options=Markup(render_state_options(state_mapping, jira.state)),
                           **jira.get_props())


@app.route('/update/', methods=['POST'])
def do_update():
    jid = request.values.get('jid')
    state = request.values.get('state')

    session = app.merge_progress.get_db_session()
    app.logger.info('Update Jira {j} state to {s}'.format(j=jid, s=state))
    session.query(MergeJira).filter_by(jid=jid).update({'state': state}, synchronize_session='evaluate')
    session.commit()

    return redirect(url_for('show_list'))


def render_statuses(status_map):
    text = ''
    for key in status_map:
        text += '<tr><td>{k}</td><td><input type="text" name="{k}" value="{v}"></td></tr>'.format(k=key,
                                                                                                  v=status_map[key])
    return text


@app.route('/edit_status/', methods=['GET'])
def do_edit_status():
    session = app.merge_progress.get_db_session()

    status_map = {}
    statuses = session.query(Status)
    for status in statuses:
        status_map[status.key] = status.value

    return render_template('edit_status.html', statuses=Markup(render_statuses(status_map)))


@app.route('/update_status/', methods=['POST'])
def do_update_status():
    session = app.merge_progress.get_db_session()

    update_map = {}
    statuses = session.query(Status)
    for status in statuses:
        new_value = request.values.get(status.key)
        if new_value != status.value:
            update_map[status.key] = new_value
    for key in update_map:
        app.logger.info('update status key {k} to {v}'.format(k=key, v=update_map[key]))
        session.query(Status).filter_by(key=key).update({'value': update_map[key]}, synchronize_session='evaluate')
    session.commit()
    return redirect(url_for('do_mgmt'))


@app.route('/add_jira/')
def add_jira():
    session = app.merge_progress.get_db_session()
    state_mapping = get_state_mappings(session)
    return render_template('add_jira.html', state_options=Markup(render_state_options(state_mapping, -1)))


@app.route('/add/', methods=['POST'])
def do_add_jira():
    session = app.merge_progress.get_db_session()
    jira = MergeJira()
    jira.jid = request.values.get('jid')
    jira.title = request.values.get('title')
    jira.state = request.values.get('state')

    existing = session.query(MergeJira).filter_by(jid=jira.jid).first()
    if existing is not None:
        error = 'JIRA exists for jid:{jid}'.format(jid=jira.jid)
        app.logger.error(error)
        return render_template('error_page.html', error=error)

    app.logger.info('Adding new JIRA {}'.format(jira))
    session.add(jira)
    session.commit()

    return redirect(url_for('do_mgmt'))


@app.route('/purge/')
def do_purge():
    session = app.merge_progress.get_db_session()
    archive_state = session.query(StateMap).filter_by(description='Archived').first()
    if archive_state is not None:
        app.logger.info('Deleting Archived JIRAs')
        session.query(MergeJira).filter_by(state=archive_state.state).delete(synchronize_session='evaluate')
        session.commit()

    return redirect(url_for('do_mgmt'))


if __name__ == '__main__':
    merge_progress = MergeProgress()
    merge_progress.set_config('merge_progress.props')
    merge_progress.set_logger(merge_progress.config.get('directories', 'log') + '/merge_progress.log')

    app.set_session(merge_progress.get_db_session())

    app.set_merge_progress(merge_progress)
    app.set_logger(merge_progress.logger)

    app.logger.info('MergeProgress app started')

    app.run(debug=True, port='5000', host='0.0.0.0')
