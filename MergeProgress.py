from sqlalchemy import Column, Integer, String
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import ConfigParser
from datetime import datetime
import json
import logging
import logging.handlers

Base = declarative_base()


def convert_to_str(var):
    if var is None:
        return ''
    else:
        return str(var)


class MergeJira(Base):
    __tablename__ = 'merge_jira'

    jid = Column(Integer, primary_key=True)
    title = Column(String)
    state = Column(Integer)
    dependent_jira = Column(Integer)
    comment = Column(String)

    def __repr__(self):
        return 'id: {id} Title: {title}: state: {state} dependent_jira: {dj} comment: {cm}'.format(id=self.jid,
                                                                                                   title=self.title,
                                                                                                   state=self.state,
                                                                                                   dj=self.dependent_jira,
                                                                                                   cm=self.comment)

    def get_properties(self):
        dependent_jira = convert_to_str(self.dependent_jira)
        comment = convert_to_str(self.comment)
        return {
            'jid': self.jid,
            'title': self.title,
            'state': self.state,
            'dependent_jira': dependent_jira,
            'comment': comment
        }


class Status(Base):
    __tablename__ = 'status'

    key = Column(String, primary_key=True)
    value = Column(String)

    def __repr__(self):
        return 'Key: {k} Value: {v}'.format(k=self.key, v=self.value)


class StateMap(Base):
    __tablename__ = 'state_map'

    state = Column(Integer, primary_key=True)
    description = Column(String)

    def __repr__(self):
        return 'State: {s} Description: {d}'.format(s=self.state, d=self.description)


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
            self.database = 'sqlite:///{dir}/{db}'.format(dir=self.config.get('directories', 'data'),
                                                          db=self.config.get('database', 'dbname'))

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
