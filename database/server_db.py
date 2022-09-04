from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, \
    create_engine, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


class ServerStorage:
    Base = declarative_base()
    
    class AllUsers(Base):
        __tablename__ = 'all_users'
        id = Column(Integer, primary_key=True)
        login = Column(String, unique=True)
        last_connect = Column(DateTime)
        passwd_hash = Column(String)
        pubkey = Column(Text)
        
        def __init__(self, login, passwd_hash):
            self.login = login
            self.last_connect = datetime.now()
            self.passwd_hash = passwd_hash
            self.pubkey = None
    
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

    class UsersContacts(Base):
        __tablename__ = 'users_contacts'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('all_users.id'))
        contact = Column(String, ForeignKey('all_users.id'))

        def __init__(self, user, contact):
            self.user = user
            self.contact = contact

    class UsersHistory(Base):
        __tablename__ = 'users_history'
        id = Column(Integer, primary_key=True)
        user = Column(String, ForeignKey('all_users.id'))
        sent = Column(Integer)
        accepted = Column(Integer)

        def __init__(self, user):
            self.user = user
            self.sent = 0
            self.accepted = 0

    def __init__(self, path):
        self.engine = create_engine('sqlite:///server_db.db3', echo=False,
                                    pool_recycle=7200,
                                    connect_args={'check_same_thread': False})
        
        self.Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        self.session.query(self.ActiveUsers).delete()
        self.session.commit()
        
    def user_login(self, username, ip_addr, port, key):
        result = self.session.query(self.AllUsers).filter_by(login=username)
        
        if result.count():
            user = result.first()
            user.last_connect = datetime.now()
            if user.pubkey != key:
                user.pubkey = key
        else:
            raise ValueError('Пользователь не зарегистрирован.')
            # user = self.AllUsers(username)
            # self.session.add(user)
            # self.session.commit()
            # user_in_history = self.UsersHistory(user.id)
            # self.session.add(user_in_history)

        new_active_user = self.ActiveUsers(user.id, ip_addr, port, 
                                           datetime.now())
        self.session.add(new_active_user)
        
        history = self.LoginHistory(user.id, ip_addr, port, datetime.now())
        self.session.add(history)
        
        self.session.commit()

    def add_user(self, name, passwd_hash):
        """Регистрация нового пользователя"""
        user_row = self.AllUsers(name, passwd_hash)
        self.session.add(user_row)
        self.session.commit()
        history_row = self.UsersHistory(user_row.id)
        self.session.add(history_row)
        self.session.commit()

    def remove_user(self, name):
        """Удаления пользователя из БД"""
        user = self.session.query(self.AllUsers).filter_by(login=name).first()
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.query(self.LoginHistory).filter_by(user=user.id).delete()
        self.session.query(self.UsersContacts).filter_by(user=user.id).delete()
        self.session.query(
            self.UsersContacts).filter_by(contact=user.id).delete()
        self.session.query(self.UsersHistory).filter_by(user=user.id).delete()
        self.session.query(self.AllUsers).filter_by(login=name).delete()
        self.session.commit()

    def get_hash(self, name):
        """Получение хэша пароля"""
        user = self.session.query(self.AllUsers).filter_by(login=name).first()
        return user.passwd_hash

    def get_pubkey(self, name):
        """Получение публичного ключа"""
        user = self.session.query(self.AllUsers).filter_by(login=name).first()
        return user.pubkey

    def check_user(self, name):
        """Проверка существования пользователя в БД"""
        if self.session.query(self.AllUsers).filter_by(login=name).count():
            return True
        else:
            return False
    
    def user_logout(self, username):
        user = self.session.query(self.AllUsers).\
            filter_by(login=username).first()
        
        self.session.query(self.ActiveUsers).filter_by(user=user.id).delete()
        self.session.commit()

    def process_message(self, sender, recipient):
        sender = self.session.query(self.AllUsers).\
            filter_by(login=sender).first().id
        reciv = self.session.query(self.AllUsers).\
            filter_by(login=recipient).first().id

        sender_row = self.session.query(self.UsersHistory).\
            filter_by(user=sender).first()
        sender_row.sent += 1
        recipient_row = self.session.query(self.UsersHistory).\
            filter_by(user=reciv).first()
        recipient_row.accepted += 1

        self.session.commit()

    def add_contact(self, user, contact):
        user = self.session.query(self.AllUsers).filter_by(login=user).first()
        contact = self.session.query(self.AllUsers).filter_by(login=contact).\
            first()

        if not contact or self.session.query(self.UsersContacts).\
                filter_by(user=user.id, contact=contact.id).count():
            return

        contact_row = self.UsersContacts(user.id, contact.id)
        self.session.add(contact_row)
        self.session.commit()

    def remove_contact(self, user, contact):
        user = self.session.query(self.AllUsers).filter_by(login=user).first()
        contact = self.session.query(self.AllUsers).filter_by(login=contact).\
            first()
        if not contact:
            return

        self.session.query(self.UsersContacts).filter(
            self.UsersContacts.user == user.id,
            self.UsersContacts.contact == contact.id).delete()
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

    def get_contacts(self, username):
        user = self.session.query(self.AllUsers).filter_by(login=username).one()

        query = self.session.query(self.UsersContacts, self.AllUsers.login).\
            filter_by(user=user.id).\
            join(self.AllUsers, self.UsersContacts.contact == self.AllUsers.id)
        return [contact[1] for contact in query.all()]

    def message_history(self):
        query = self.session.query(
            self.AllUsers.login,
            self.AllUsers.last_connect,
            self.UsersHistory.sent,
            self.UsersHistory.accepted
        ).join(self.AllUsers)

        return query.all()


if __name__ == '__main__':
    pass
    # db = ServerStorage()
    # db.user_login('client_1', '192.168.1.4', 8888)
    # db.user_login('client_2', '192.168.1.5', 7777)
    #
    # print(db.active_users_list())
    #
    # db.user_logout('client_1')
    # print(db.users_list())
    # print(db.active_users_list())
    # db.user_logout('client_2')
    # print(db.users_list())
    # print(db.active_users_list())
    #
    # print(db.login_history())
    # print(db.users_list())


    # test_db = ServerStorage('server_base.db3')
    # test_db.user_login('client_3', '192.168.1.4', 7878)
    # test_db.user_login('client_4', '192.168.1.5', 7779)
    # test_db.user_login('1111', '192.168.1.113', 8080)
    # test_db.user_login('McG2', '192.168.1.113', 8081)
    # # print(test_db.users_list())
    # # print(test_db.active_users_list())
    # test_db.user_logout('McG2')
    # # print(test_db.login_history('re'))
    # test_db.add_contact('client_2', 'client_1')
    # test_db.add_contact('client_1', 'client_2')
    # test_db.add_contact('McG2', '1111')
    # test_db.remove_contact('client_2', 'client_1')
    # test_db.process_message('client_3', 'client_4')
    # # print(test_db.message_history())