class DtObject:
    def toMap(self):
        pass


class SuccessPacket(DtObject):
    def toMap(self):
        return {
            'packet_type': 'success'
        }

class SuccessPacketWithPayload(DtObject):
    def __init__(self, payload):
        self.payload = payload

    def toMap(self):
        return {
            'packet_type': 'success_with_payload',
            'payload': self.payload
        }

class FailurePacket(DtObject):
    def toMap(self):
        return {
            'packet_type': 'failure'
        }

class LoginSuccessPacket(DtObject):
    def __init__(self, token, expiry, role, username, id):
        self.token = token
        self.expiry = expiry
        self.role = role
        self.username = username
        self.id = id

    def toMap(self):
        return {
            'packet_type': 'login_success',
            'token': self.token,
            'expiry': self.expiry,
            'role': self.role,
            'username': self.username,
            'id': self.id
        }

class LoginErrorPacket(DtObject):
    def __init__(self):
        pass

    def toMap(self):
        return {
            'packet_type': 'login_error'
        }

class RegisterSuccessPacket(DtObject):
    def __init__(self, token, expiry, id):
        self.token = token
        self.expiry = expiry
        self.id = id

    def toMap(self):
        return {
            'packet_type': 'register_success',
            'token': self.token,
            'expiry': self.expiry,
            'id': self.id
        }

class RegisterErrorPacket(DtObject):
    def __init__(self):
        pass

    def toMap(self):
        return {
            'packet_type': 'register_error'
        }

class InvalidRequestErrorPacket(DtObject):
    def __init__(self):
        pass

    def toMap(self):
        return {
            'packet_type': 'invalid_request_error'
        }

class NotLoggedInErrorPacket(DtObject):
    def __init__(self):
        pass

    def toMap(self):
        return {
            'packet_type': 'not_logged_in_error'
        }

class LogoutSuccessPacket(DtObject):
    def __init__(self):
        pass

    def toMap(self):
        return {
            'packet_type': 'logout_success'
        }


class MataKuliahDto(DtObject):
    def __init__(self, id, nama, kelas):
        self.id = id
        self.nama = nama
        self.kelas = kelas

    def toMap(self):
        return {
            'packet_type': 'mata_kuliah_dto',
            'id': self.id,
            'nama': self.nama,
            'kelas': [kelas.toMap() for kelas in self.kelas]
        }

class KelasMataKuliahDto(DtObject):
    def __init__(self, id, nama, list_anggota, list_jadwal):
        self.id = id
        self.nama = nama
        self.list_anggota = list_anggota
        self.list_jadwal = list_jadwal


    def toMap(self):
        return {
            'packet_type': 'kelas_mata_kuliah_dto',
            'id': self.id,
            'nama': self.nama,
            'list_anggota': [anggota.toMap() for anggota in self.list_anggota],
            'list_jadwal': [jadwal.toMap() for jadwal in self.list_jadwal]
        }

class AnggotaKelasDto(DtObject):
    def __init__(self, username, id_user):
        self.username = username
        self.id_user = id_user

    def toMap(self):
        return {
            'packet_type': 'anggota_kelas_dto',
            'username': self.username,
            'id_user': self.id_user
        }


class JadwalKelasDto(DtObject):
    def __init__(self, id, hari, jam_mulai, jam_selesai, status):
        self.id = id
        self.hari = hari
        self.jam_mulai = jam_mulai
        self.jam_selesai = jam_selesai
        self.status = status

    def toMap(self):
        return {
            'packet_type': 'jadwal_kelas_dto',
            'id': self.id,
            'hari': self.hari,
            'jam_mulai': self.jam_mulai,
            'jam_selesai': self.jam_selesai,
            'status': self.status
        }

class RiwayatPresensiDto(DtObject):
    def __init__(self, id, tanggal, status):
        self.id = id
        self.tanggal = tanggal
        self.status = status

    def toMap(self):
        return {
            'packet_type': 'riwayat_presensi_dto',
            'id': self.id,
            'tanggal': self.tanggal,
            'status': self.status
        }
