from sqlalchemy import Column, Integer, String
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from flask import render_template
from flask import Markup

import ConfigParser
from datetime import datetime
import json
import logging
import logging.handlers


Base = declarative_base()


state_mapping = {1: 'Pending Dev Commit', 2: 'Pending Merge', 3: 'Merge in Progress', 4: 'Merged'}
state_class_map = {1: 'pending', 2: 'pending', 3: 'testing', 4: 'merged'}

def get_state_class(state):
    return state_class_map[state]

class MergeJira(Base):
    __tablename__ = 'merge_jira'

    jid = Column(Integer, primary_key = True)
    title = Column(String)
    state = Column(Integer)


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

    def __repr__(self):
        return 'id: {id} Title: {title}: state: {state}'.format(id=self.jid, title=self.title, state=self.state)


class Status(Base):
    __tablename__ = 'status'

    key = Column(String, primary_key = True)
    value = Column(String)

    def __repr__(self):
        return 'Key: {k} Value: {v}'.format(k=self.key, v=self.value)


class MergeProgress:
    def __init__(self, **kwargs):
        self.config = None
        self.session = None
        self.database = None
        self.session = None
        self.logger = None


    def set_logger(self, filename):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        fh = logging.handlers.TimedRotatingFileHandler(filename, when='midnight', interval=1)
        fh.setLevel(logging.DEBUG)
        fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fh.setFormatter(fmt)
        self.logger.addHandler(fh)


    def set_config(self, *config_files):
        self.config = ConfigParser.SafeConfigParser()
        for file in config_files:
            self.config.read(file)

        try:
            self.database = 'sqlite:///{dir}/{db}'.format(dir=self.config.get('directories', 'data'), db=self.config.get('database', 'dbname'))
    
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError) as var:
            print(var)


    def get_db_session(self, echo=False):
        engine = create_engine(self.database, echo=echo)
        Base.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)
        self.session = Session()
        return self.session


if __name__ == '__main__':
    print('Test')
    merge_progress = MergeProgress()
    merge_progress.set_config('merge_progress.props', 'merge_progress.local.props')

    session = merge_progress.get_db_session(echo=True)

    stats = session.query(Status)
    for s in stats:
        print(s)

    jiras = session.query(MergeJira)
    for j in jiras:
        print(j)



    session.commit()
