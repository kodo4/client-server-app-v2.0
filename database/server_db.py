from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, \
    create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


class ServerStorage:
    Base = declarative_base()
    
    class AllUsers(Base):
        __tablename__ = 'all_users'
        id = Column(Integer, primary_key=True)
        login = Column(String, unique=True)
        last_connect = Column(DateTime)
        
        def __init__(self, login):
            self.login = login
            self.last_connect = datetime.now()
    
    class ActiveUsers(Base):
        __tablename__ = 'active_users'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('all_users.id'), unique=True)
        ip = Column(String)
        port = Column(Integer)
        time_connect = Column(DateTime)
        
        def __init__(self, user, ip, port, time_connect):
            self.user = user
            self.ip = ip
            self.port = port
            self.time_connect = time_connect
    
    class LoginHistory(Base):
        __tablename__ = 'login_history'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('all_users.id'))
        ip = Column(String)
        port = Column(Integer)
        last_connection = Column(DateTime)
        
        def __init__(self, user, ip, port, last_connection):
            self.user = user
            self.ip = ip
            self.port = port
            self.last_connection = last_connection
    
    def __init__(self):
        self.engine = create_engine('sqlite:///server_db.db3', echo=False)
        
        self.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()
        
    def user_login(self, username, ip_addr, port):
        result = self.session.query(self.AllUsers).filter_by(login=username)
        
        if result.count():
            user = result.first()
            user.last_connect = datetime.now()
        else:
            user = self.AllUsers(username)
            self.session.add(user)
            self.session.commit()
        
        new_active_user = self.ActiveUsers(user.id, ip_addr, port, 
                                           datetime.now())
        self.session.add(new_active_user)
        
        history = self.LoginHistory(user.id, ip_addr, port, datetime.now())
        self.session.add(history)
        
        self.session.commit()
    
    def user_logout(self, username):
        user = self.session.query(self.AllUsers).\
            filter_by(login=username).first()
        
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.commit()
        
    def users_list(self):
        query = self.session.query(
            self.AllUsers.login,
            self.AllUsers.last_connect
        )
        return query.all()
    
    def active_users_list(self):
        query = self.session.query(
            self.AllUsers.login,
            self.ActiveUsers.ip,
            self.ActiveUsers.port,
            self.ActiveUsers.time_connect
        ).join(self.AllUsers)
        return query.all()
    
    def login_history(self, username=None):
        query = self.session.query(
            self.AllUsers.login,
            self.LoginHistory.last_connection,
            self.LoginHistory.ip,
            self.LoginHistory.port
        ).join(self.AllUsers)
        if username:
            query = query.filter(self.AllUsers.login == username)
        return query.all()


if __name__ == '__main__':
    db = ServerStorage()
    db.user_login('client_1', '192.168.1.4', 8888)
    db.user_login('client_2', '192.168.1.5', 7777)

    print(db.active_users_list())

    db.user_logout('client_1')
    print(db.users_list())
    print(db.active_users_list())
    db.user_logout('client_2')
    print(db.users_list())
    print(db.active_users_list())

    print(db.login_history())
    print(db.users_list())
