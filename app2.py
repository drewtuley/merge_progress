from flask import Flask
from flask import render_template
from flask import Markup
from flask import send_from_directory
import os
from datetime import datetime
from MergeProgress import MergeProgress 
from MergeProgress import MergeJira
from MergeProgress import Status


class App(Flask):
    logger = None
    merge_progress = None
    session = None

    def set_logger(self, logger):
        self.logger = logger

    def set_merge_progress(self, merge_progress):
        self.merge_progress = merge_progress

    def set_session(self, session):
        self.session = session;


app = App(__name__)

def get_state_class(state):
    return state_class_map[state]


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/progress/', methods=['GET'])
def do_progress():
    session = app.merge_progress.get_db_session()
    jiras = session.query(MergeJira).order_by('state')

    table = '<table width="100%">'
    for jira in jiras:
        table += jira.markup_row()
    table += '</table>'

    updated = session.query(Status).filter_by(key='updated').first()
    rebased = session.query(Status).filter_by(key='rebased').first()
    head_sha = session.query(Status).filter_by(key='head_sha').first()

    return render_template('merge_progress.html', data=Markup(table), date=str(datetime.now()), updated=Markup(updated.value),
                           rebased=Markup(rebased.value), head_sha=Markup(head_sha.value))


if __name__ == '__main__':
    merge_progress = MergeProgress()
    merge_progress.set_config('merge_progress.props')
    merge_progress.set_logger(merge_progress.config.get('directories','log')+'/merge_progress.log')

    app.set_session(merge_progress.get_db_session())

    app.set_merge_progress(merge_progress)
    app.set_logger(merge_progress.logger)

    app.logger.info('MergeProgress app started') 
  
    app.run(debug=True, port='5000', host='0.0.0.0')
