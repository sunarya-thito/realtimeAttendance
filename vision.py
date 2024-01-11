import datetime
import threading
import cv2
import face_recognition
import numpy as np

import database
import websocket

RUNNING = True


def start_camera():
    threading.Thread(target=start_server).start()


def push_user_ids(user_ids):
    # cari semua jadwal untuk sekarang
    now = datetime.datetime.now()
    jadwals = database.JadwalKelas.select().where(
        (database.JadwalKelas.jam_mulai <= now.hour * 60 + now.minute) &
        (database.JadwalKelas.jam_selesai >= now.hour * 60 + now.minute) &
        (database.JadwalKelas.hari == now.weekday()))
    anggota = [] # list of list of anggota
    for jadwal in jadwals:
        anggota_list = database.AnggotaKelas.select().where(
            database.AnggotaKelas.kelas_mata_kuliah == jadwal.kelas_mata_kuliah)
        anggota.append(anggota_list)
    for user_id in user_ids:
        for i in range(len(anggota)):
            for j in range(len(anggota[i])):
                print(anggota[i][j].user.id, user_id)
                if anggota[i][j].user.id == user_id:
                    print('user {} masuk ke kelas {}'.format(user_id, jadwals[i].kelas_mata_kuliah.nama))
                    # user_id masuk ke kelas i
                    jadwal = jadwals[i]
                    try:
                        database.RiwayatPresensi.create(jadwal_kelas=jadwal, user=user_id, waktu=now,
                                                        tahun=now.year, bulan=now.month, tanggal=now.day)
                        websocket.broadcast_packet(websocket.HadirPacket(user_id))
                    except Exception as e:
                        pass
                    break


def start_server():
    print('starting camera')
    camera = cv2.VideoCapture(0)
    user_ids = set()
    while RUNNING:
        _, frame = camera.read()
        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)
        db_face_encodings = database.face_encodings
        mapped_db_face_encodings = [db_face_encoding['face_encoding'] for db_face_encoding in db_face_encodings]
        # draw rectangle
        current_user_ids = set()
        # find face
        for i in range(len(face_encodings)):
            face_encoding = face_encodings[i]
            # left, top, right, bottom = face_locations[i]
            top, right, bottom, left = face_locations[i]
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            # FIX: flip both
            matches = face_recognition.compare_faces(mapped_db_face_encodings, face_encoding)
            # find the best match
            face_distances = face_recognition.face_distance(mapped_db_face_encodings, face_encoding)
            if len(face_distances) == 0:
                continue
            best_match_index = np.argmin(face_distances)
            distance_best_match = face_distances[best_match_index]
            if matches[best_match_index] and distance_best_match < 0.4:
                username = db_face_encodings[best_match_index]['username']
                user_id = db_face_encodings[best_match_index]['user_id']
                # draw text
                # left, top, right, bottom = face_locations[best_match_index]
                # cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
                cv2.putText(frame, username, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 1)
                current_user_ids.add(user_id)

        for user_id in user_ids - current_user_ids:
            print('user {} keluar'.format(user_id))

        masuk = current_user_ids - user_ids
        for user_id in masuk:
            print('user {} masuk'.format(user_id))

        push_user_ids(masuk)

        user_ids = current_user_ids
        cv2.imshow('camera', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
