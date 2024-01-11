import asyncio
import base64
import contextlib
import datetime
import pickle
import threading

import cv2
import numpy as np
import websockets
from fastapi import FastAPI, Body
import database
import dto
import vision
import face_recognition
from fastapi.middleware.cors import CORSMiddleware

import websocket
import uvicorn

app = FastAPI()




# allow all origins
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"])


# shutdown hook
@app.on_event("shutdown")
def shutdown_event():
    print('shutting down')
    vision.RUNNING = False





@app.get("/login")
def login(key: str, password: str):
    user = database.User.select().where((database.User.username == key) | (database.User.email == key) &
                                        (database.User.password == password)).first()
    if user is not None:
        token = database.generate_token()
        expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
        database.UserSession.create(user=user, token=token, expiry=expiry)
        role = user.role
        return dto.LoginSuccessPacket(token, expiry, role, user.username, user.id).toMap()
    else:
        return dto.LoginErrorPacket().toMap()


@app.get("/register")
def register(username: str, email: str, password: str):
    if not database.validate_username(username):
        return dto.InvalidRequestErrorPacket().toMap()
    if not database.email_validate(email):
        return dto.InvalidRequestErrorPacket().toMap()
    if not database.validate_password(password):
        return dto.InvalidRequestErrorPacket().toMap()
    try:
        user = database.User.create(username=username, email=email, password=password)
        token = database.generate_token()
        expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
        database.UserSession.create(user=user, token=token, expiry=expiry)
        return dto.RegisterSuccessPacket(token, expiry, user.id).toMap()
    except Exception as e:
        print(e)
        return dto.RegisterErrorPacket().toMap()


@app.get("/logout")
def logout(token: str):
    database.UserSession.delete().where(database.UserSession.token == token).execute()
    return dto.LogoutSuccessPacket().toMap()


@app.get("/set_username")
def set_username(token: str, username: str):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.InvalidRequestErrorPacket().toMap()

    user = user_session.user
    user.name = username
    # user.name is unique, so if there is another user with the same name, it will raise an exception
    try:
        user.save()
        return dto.SuccessPacket().toMap()
    except Exception as e:
        print(e)
        return dto.InvalidRequestErrorPacket().toMap()


@app.post("/set_face")
def set_face(token: str, image: str = Body(...)):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.InvalidRequestErrorPacket().toMap()
    user = user_session.user
    # image is base64 encoded
    # substring to remove the 'data:image/jpeg;base64,' part
    img = image[23:]
    # decode base64
    img = base64.b64decode(img)
    # decode the image
    img = cv2.imdecode(np.fromstring(img, np.uint8), cv2.IMREAD_UNCHANGED)
    # convert to RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    encodings = face_recognition.face_encodings(img)
    if len(encodings) == 0:
        return dto.InvalidRequestErrorPacket().toMap()
    face_encoding = encodings[0]
    database.set_face_encoding(user, face_encoding)
    # using pickle to convert face encoding to blob
    byte_array = pickle.dumps(face_encoding)
    user.face_encoding = byte_array
    user.save()
    return dto.SuccessPacket().toMap()


@app.get("/create_matkul")
def create_matkul(token: str, nama: str):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.InvalidRequestErrorPacket().toMap()
    user = user_session.user
    if user.role != 'admin':
        return dto.InvalidRequestErrorPacket().toMap()
    mata_kuliah = database.MataKuliah.create(nama=nama)
    return dto.SuccessPacketWithPayload(mata_kuliah.id).toMap()


@app.get("/create_kelas")
def create_kelas(token: str, mata_kuliah_id: int, nama: str):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.InvalidRequestErrorPacket().toMap()
    user = user_session.user
    if user.role != 'admin':
        return dto.InvalidRequestErrorPacket().toMap()
    mata_kuliah = database.MataKuliah.select().where(database.MataKuliah.id == mata_kuliah_id).first()
    if mata_kuliah is None:
        return dto.InvalidRequestErrorPacket().toMap()
    kelas = database.KelasMataKuliah.create(mata_kuliah=mata_kuliah, nama=nama)
    return dto.SuccessPacketWithPayload(kelas.id).toMap()


@app.get("/join_kelas")
def join_kelas(token: str, kelas_id: int):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.NotLoggedInErrorPacket().toMap()
    user = user_session.user
    kelas = database.KelasMataKuliah.select().where(database.KelasMataKuliah.id == kelas_id).first()
    if kelas is None:
        return dto.InvalidRequestErrorPacket().toMap()
    anggota = database.AnggotaKelas.create(kelas_mata_kuliah=kelas, user=user)
    return dto.SuccessPacketWithPayload(-1).toMap()


@app.get("/leave_kelas")
def leave_kelas(token: str, kelas_id: int):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.NotLoggedInErrorPacket().toMap()
    user = user_session.user
    kelas = database.KelasMataKuliah.select().where(database.KelasMataKuliah.id == kelas_id).first()
    if kelas is None:
        return dto.InvalidRequestErrorPacket().toMap()
    anggota = database.AnggotaKelas.select().where((database.AnggotaKelas.kelas_mata_kuliah == kelas) &
                                                   (database.AnggotaKelas.user == user)).first()
    if anggota is None:
        return dto.InvalidRequestErrorPacket().toMap()
    anggota.delete_instance()
    return dto.SuccessPacket().toMap()


@app.get("/add_jadwal")
def add_jadwal(token: str, kelas_id: int, hari: int, jam_mulai: int, jam_selesai: int):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.InvalidRequestErrorPacket().toMap()
    user = user_session.user
    if user.role != 'admin':
        return dto.InvalidRequestErrorPacket().toMap()
    kelas = database.KelasMataKuliah.select().where(database.KelasMataKuliah.id == kelas_id).first()
    if kelas is None:
        return dto.InvalidRequestErrorPacket().toMap()
    jadwal = database.JadwalKelas.create(kelas_mata_kuliah=kelas, hari=hari, jam_mulai=jam_mulai,
                                         jam_selesai=jam_selesai)
    return dto.SuccessPacketWithPayload(jadwal.id).toMap()


@app.get("/hapus_matkul")
def hapus_matkul(token: str, mata_kuliah_id: int):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.InvalidRequestErrorPacket().toMap()
    user = user_session.user
    if user.role != 'admin':
        return dto.InvalidRequestErrorPacket().toMap()
    mata_kuliah = database.MataKuliah.select().where(database.MataKuliah.id == mata_kuliah_id).first()
    if mata_kuliah is None:
        return dto.InvalidRequestErrorPacket().toMap()
    mata_kuliah.delete_instance()
    return dto.SuccessPacket().toMap()


@app.get("/hapus_kelas")
def hapus_kelas(token: str, kelas_id: int):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.InvalidRequestErrorPacket().toMap()
    user = user_session.user
    if user.role != 'admin':
        return dto.InvalidRequestErrorPacket().toMap()
    kelas = database.KelasMataKuliah.select().where(database.KelasMataKuliah.id == kelas_id).first()
    if kelas is None:
        return dto.InvalidRequestErrorPacket().toMap()
    kelas.delete_instance()
    return dto.SuccessPacket().toMap()


@app.get("/hapus_anggota")
def hapus_anggota(token: str, anggota_id: int):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.InvalidRequestErrorPacket().toMap()
    user = user_session.user
    if user.role != 'admin':
        return dto.InvalidRequestErrorPacket().toMap()
    anggota = database.AnggotaKelas.select().where(database.AnggotaKelas.user == anggota_id).first()
    if anggota is None:
        return dto.InvalidRequestErrorPacket().toMap()
    anggota.delete_instance()
    return dto.SuccessPacket().toMap()


@app.get("/hapus_jadwal")
def hapus_jadwal(token: str, jadwal_id: int):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.InvalidRequestErrorPacket().toMap()
    user = user_session.user
    if user.role != 'admin':
        return dto.InvalidRequestErrorPacket().toMap()
    jadwal = database.JadwalKelas.select().where(database.JadwalKelas.id == jadwal_id).first()
    if jadwal is None:
        return dto.InvalidRequestErrorPacket().toMap()
    jadwal.delete_instance()
    return dto.SuccessPacket().toMap()


@app.get("/edit_matkul")
def edit_matkul(token: str, mata_kuliah_id: int, nama: str):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.NotLoggedInErrorPacket().toMap()
    user = user_session.user
    if user.role != 'admin':
        return dto.InvalidRequestErrorPacket().toMap()
    mata_kuliah = database.MataKuliah.select().where(database.MataKuliah.id == mata_kuliah_id).first()
    if mata_kuliah is None:
        return dto.InvalidRequestErrorPacket().toMap()
    mata_kuliah.nama = nama
    mata_kuliah.save()
    return dto.SuccessPacket().toMap()


@app.get("/edit_kelas")
def edit_kelas(token: str, kelas_id: int, nama: str):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.NotLoggedInErrorPacket().toMap()
    user = user_session.user
    if user.role != 'admin':
        return dto.InvalidRequestErrorPacket().toMap()
    kelas = database.KelasMataKuliah.select().where(database.KelasMataKuliah.id == kelas_id).first()
    if kelas is None:
        return dto.InvalidRequestErrorPacket().toMap()
    kelas.nama = nama
    kelas.save()
    return dto.SuccessPacket().toMap()


@app.get("/edit_jadwal")
def edit_jadwal(token: str, jadwal_id: int, hari: int, jam_mulai: int, jam_selesai: int):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.NotLoggedInErrorPacket().toMap()
    user = user_session.user
    if user.role != 'admin':
        return dto.InvalidRequestErrorPacket().toMap()
    jadwal = database.JadwalKelas.select().where(database.JadwalKelas.id == jadwal_id).first()
    if jadwal is None:
        return dto.InvalidRequestErrorPacket().toMap()
    jadwal.hari = hari
    jadwal.jam_mulai = jam_mulai
    jadwal.jam_selesai = jam_selesai
    jadwal.save()
    return dto.SuccessPacket().toMap()


@app.get("/get_semua_matkul")
def get_semua_matkul(token: str):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.NotLoggedInErrorPacket().toMap()
    mata_kuliah = database.MataKuliah.select()
    mata_kuliah_dto = []
    for matkul in mata_kuliah:
        kelas = database.KelasMataKuliah.select().where(database.KelasMataKuliah.mata_kuliah == matkul)
        kelas_dto = []
        for k in kelas:
            jadwal = database.JadwalKelas.select().where(database.JadwalKelas.kelas_mata_kuliah == k)
            jadwal_dto = []
            for j in jadwal:
                first_riwayat = database.RiwayatPresensi.select().where(
                    (database.RiwayatPresensi.jadwal_kelas == j) &
                    (database.RiwayatPresensi.user == user_session.user)).first()
                # check if week is the same
                status = 'tidak_hadir'
                if first_riwayat is not None:
                    # cek kalau jadwal sedang berlangsung
                    now = datetime.datetime.now()
                    if j.hari == now.weekday() and j.jam_mulai <= now.hour * 60 + now.minute <= j.jam_selesai:
                        # kalau sedang berlangsung, cek apakah sudah presensi
                        if first_riwayat.tahun == now.year and first_riwayat.bulan == now.month and first_riwayat.tanggal == now.day:
                            status = 'hadir'
                    else:

                        # jika tidak sedang berlangsung, tandai sebagai hadir
                        status = 'hadir'

                jadwal_dto.append(dto.JadwalKelasDto(j.id, j.hari, j.jam_mulai, j.jam_selesai, status))
            anggota = database.AnggotaKelas.select().where(database.AnggotaKelas.kelas_mata_kuliah == k)
            anggota_dto = []
            for a in anggota:
                anggota_dto.append(dto.AnggotaKelasDto(a.user.username, a.user.id))
            kelas_dto.append(dto.KelasMataKuliahDto(k.id, k.nama, anggota_dto, jadwal_dto))
        mata_kuliah_dto.append(dto.MataKuliahDto(matkul.id, matkul.nama, kelas_dto).toMap())
    return dto.SuccessPacketWithPayload(mata_kuliah_dto).toMap()


@app.get("/get_riwayat")
def get_riwayat(token: str, jadwal_kelas_id: int):
    user_session = database.UserSession.select().where(database.UserSession.token == token).first()
    if user_session is None:
        return dto.NotLoggedInErrorPacket().toMap()
    riwayat = database.RiwayatPresensi.select().where(database.RiwayatPresensi.jadwal_kelas == jadwal_kelas_id)
    riwayat_dto = []
    for r in riwayat:
        riwayat_dto.append(dto.RiwayatPresensiDto(-1, r.waktu, 'hadir').toMap())
    return dto.SuccessPacketWithPayload(riwayat_dto).toMap()

def run_fastapi_server():
    uvicorn.run(app, host="localhost", port=8000)

@contextlib.contextmanager
def start_fastapi_server():
    thread = threading.Thread(target=run_fastapi_server)
    thread.start()

print('initializing database')
database.initDatabase()
database.load_face_encodings()
vision.start_camera()
async def start_websocket_server():
    start_server = websockets.serve(websocket.echo, "localhost", 8777)
    async with start_server:
        print('websocket server started')
        await asyncio.Future()
        print('websocket server stopped')
start_fastapi_server()
asyncio.get_event_loop().run_until_complete(start_websocket_server())