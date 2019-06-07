from flask import Flask
from flask import render_template
from flask import Markup
from flask import send_from_directory
import os
from datetime import datetime


class MergingJira:
    def __init__(self, jid, title, state):
        self.jid = jid
        self.title = title
        self.state = state

    def render_jira_id(self):
        return render_template('jira_id.html', id=self.jid)

    def render_jira_title(self):
        return render_template('jira_title.html', title=self.title)

    def render_jira_state(self):
        return render_template('jira_state.html', state=state_mapping[self.state])

    def markup_row(self):
        row_data = '{jid}{jtitle}{jstate}'.format(jid=self.render_jira_id(), jtitle=self.render_jira_title(),
                                                  jstate=self.render_jira_state())
        return render_template('progress_row.html', row_cls=get_state_class(self.state), row_data=Markup(row_data))


app = Flask(__name__)
state_mapping = {1: 'Pending Dev Commit', 2: 'Pending Merge', 3: 'Merge in Progress', 4: 'Merged'}
state_class_map = {1: 'pending', 2: 'pending', 3: 'testing', 4: 'merged'}


def get_state_class(state):
    return state_class_map[state]


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/progress/', methods=['GET'])
def do_progress():
    jira_map = {1: [], 2: [], 3: [], 4: []}
    with open('progress.txt') as fd:
        for line in fd:
            fields = line.strip().split('|')
            state = int(fields[2])
            jira = MergingJira(fields[0], fields[1], state)
            map = jira_map[state]
            map.append(jira)

    update_txt = ''
    with open('update.txt') as fd:
        for line in fd:
            fields = line.strip().split('|')
            if len(fields) == 2:
                if fields[0] == 'updated':
                    updated = '{u}'.format(u=fields[1])
                elif fields[0] == 'rebased':
                    rebased = '{u}'.format(u=fields[1])

    table = '<table width="100%">'
    for state in jira_map.keys():
        for jira in jira_map[state]:
            table += jira.markup_row()
    table += '</table>'

    return render_template('merge_progress.html', data=Markup(table), date=str(datetime.now()), updated=Markup(updated),
                           rebased=Markup(rebased))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
