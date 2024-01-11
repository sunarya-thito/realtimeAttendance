import datetime
import pickle
import secrets
from email_validator import validate_email, EmailNotValidError

from peewee import *

db = MySQLDatabase('realtimeattendance', user='root', password='', host='localhost', port=3306)


class MediumBlobField(BlobField):
    field_type = 'MEDIUMBLOB'


class User(Model):
    email = CharField()
    username = CharField()
    password = CharField()
    role = CharField()
    face_encoding = MediumBlobField(null=True)

    class Meta:
        database = db
        indexes = (
            (['username'], True),
        )


class UserSession(Model):
    user = ForeignKeyField(User, backref='user', on_delete='CASCADE', on_update='CASCADE')
    token = CharField()
    expiry = DateTimeField()

    class Meta:
        database = db


class MataKuliah(Model):
    nama = CharField()

    class Meta:
        database = db


class KelasMataKuliah(Model):
    mata_kuliah = ForeignKeyField(MataKuliah, backref='mata_kuliah', on_delete='CASCADE', on_update='CASCADE')
    nama = CharField()

    class Meta:
        database = db


class AnggotaKelas(Model):
    kelas_mata_kuliah = ForeignKeyField(KelasMataKuliah, backref='kelas_mata_kuliah', on_delete='CASCADE',
                                        on_update='CASCADE')
    user = ForeignKeyField(User, backref='user', on_delete='CASCADE', on_update='CASCADE')

    class Meta:
        database = db
        indexes = (
            (('kelas_mata_kuliah', 'user'), True),
        )
        primary_key = CompositeKey('kelas_mata_kuliah', 'user')


class JadwalKelas(Model):
    kelas_mata_kuliah = ForeignKeyField(KelasMataKuliah, backref='kelas_mata_kuliah', on_delete='CASCADE',
                                        on_update='CASCADE')
    # senin = 0, selasa = 1, rabu = 2, kamis = 3, jumat = 4, sabtu = 5, minggu = 6
    hari = IntegerField()
    # format 24 jam dalam satuan menit
    jam_mulai = IntegerField()
    jam_selesai = IntegerField()

    class Meta:
        database = db

class RiwayatPresensi(Model):
    user = ForeignKeyField(User, backref='user', on_delete='CASCADE', on_update='CASCADE')
    jadwal_kelas = ForeignKeyField(JadwalKelas, backref='jadwal_kelas', on_delete='CASCADE', on_update='CASCADE', null=True)
    waktu = DateTimeField()
    tahun = IntegerField()
    bulan = IntegerField()
    tanggal = IntegerField()

    class Meta:
        database = db
        indexes = (
            (('user', 'jadwal_kelas', 'tahun', 'bulan', 'tanggal'), True),
        )
        primary_key = CompositeKey('user', 'jadwal_kelas', 'tahun', 'bulan', 'tanggal')


face_encodings = []


def load_face_encodings():
    for user in User.select().where(User.face_encoding.is_null(False)):
        try:
            raw_face_encoding = user.face_encoding
            # raw_face_encoding is a bytes object
            # load usnig pickle
            face_encoding = pickle.loads(raw_face_encoding)
            face_encodings.append({
                'username': user.username,
                'user_id': user.id,
                'face_encoding': face_encoding
            })
        except Exception as e:
            print(e)


def set_face_encoding(user, face_encoding):
    # replace existing face encoding
    for i in range(len(face_encodings)):
        if face_encodings[i]['user_id'] == user.id:
            face_encodings[i]['face_encoding'] = face_encoding
            return
    # add new face encoding
    face_encodings.append({
        'username': user.username,
        'user_id': user.id,
        'face_encoding': face_encoding
    })


def hadir(user_id):
    waktu = datetime.datetime.now()
    tanggal = datetime.datetime.now()
    # ubah waktu hanya ke tanggal (jam, menit, detik dihapus)
    tanggal = tanggal.replace(hour=0, minute=0, second=0, microsecond=0)
    # jam_selesai dan jam_mulai adalah waktu dalam satuan menit
    jadwal_kelas = JadwalKelas.select().where(
        (JadwalKelas.jam_mulai <= waktu.hour * 60 + waktu.minute) &
        (JadwalKelas.jam_selesai >= waktu.hour * 60 + waktu.minute) &
        (JadwalKelas.hari == tanggal.weekday())).first()
    if jadwal_kelas is not None:
        try:
            RiwayatPresensi.create(jadwal_kelas=jadwal_kelas, user=user_id, waktu=waktu)
            return True
        except IntegrityError:
            return False
    else:
        return False


def initDatabase():
    db.connect()
    # drop tables
    # db.drop_tables([User, UserSession, MataKuliah, KelasMataKuliah, AnggotaKelas, JadwalKelas, RiwayatPresensi])
    db.create_tables([User, UserSession, MataKuliah, KelasMataKuliah, AnggotaKelas, JadwalKelas, RiwayatPresensi])


def generate_token():
    token = secrets.token_hex(32)
    return token


def validate_username(username: str):
    # username must be at least 4 characters long
    if len(username) < 4:
        return False
    # username must be alphanumeric
    if not username.isalnum():
        return False
    # username must not contain spaces or special characters
    if not username.isascii():
        return False
    # username must not contain spaces or special characters
    if ' ' in username:
        return False
    # maximum length of username is 32 characters
    if len(username) > 32:
        return False
    return True


def email_validate(email: str):
    try:
        validate_email(email)
        return True
    except EmailNotValidError:
        return False


def validate_password(password: str):
    # password must be at least 8 characters long
    return True
