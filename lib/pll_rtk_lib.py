import math, time, datetime, sys, threading, subprocess
from subprocess import PIPE
from pyproj import Transformer
import os
import io


class NMEA:
    mode_names = {0: 'NA', 1: 'Standalone', 2: 'DGNSS', 4: 'RTK Fixed', 5: 'RTK Float'}

    @classmethod
    def dm_to_sd(cls, dm):
        x = float(dm)
        d = x // 100
        m = (x - d * 100) / 60
        return d + m

    @classmethod
    def hms_to_sec(cls, hms):
        d = [int(c) for c in hms if c != '.']
        h = d[0] * 10 + d[1]
        m = d[2] * 10 + d[3]
        s = d[4] * 10 + d[5] + d[6] * 0.1 + d[7] * 0.01
        t = h * 3600 + m * 60 + s
        return t

    @classmethod
    def knot_to_meters(cls, knot):
        v = float(knot) * 1852 / 3600
        return v

    @classmethod
    def parse_GGA(cls, line):
        ds = line.strip().split(',')
        if ds[0][3:6] == 'GGA' and ds[1] != '' and ds[2] != '' and ds[4] != '' and ds[6] != '' and ds[9] != '':
            t = NMEA.hms_to_sec(ds[1])
            lat = NMEA.dm_to_sd(ds[2])
            lon = NMEA.dm_to_sd(ds[4])
            mode = int(ds[6])
            alt = float(ds[9])
            return t, lat, lon, mode, alt
        else:
            return None

    @classmethod
    def parse_RMC(cls, line):
        ds = line.strip().split(',')
        if ds[0][3:6] == 'RMC' and ds[3] != '' and ds[5] != '' and ds[7] != '':
            t = NMEA.hms_to_sec(ds[1])
            lat = NMEA.dm_to_sd(ds[3])
            lon = NMEA.dm_to_sd(ds[5])
            vel = NMEA.knot_to_meters(ds[7])
            theta = float(ds[8]) if ds[8] != '' else -1
            return t, lat, lon, vel, theta
        else:
            return None
    
    def load(self, fn):
        self.lines = open(fn).readlines()
        dict = {}
        for line in self.lines:
            r = NMEA.parse_GGA(line)
            if r is not None:
                t, lat, lon, mode, alt = r
                if t not in dict:
                    dict[t] = {}
                dict[t]['lat'] = lat
                dict[t]['lon'] = lon
                dict[t]['mode'] = mode
                dict[t]['alt'] = alt
                continue

            r = NMEA.parse_RMC(line)
            if r is not None:
                t, lat, lon, vel, theta = r
                if t not in dict:
                    dict[t] = {}
                dict[t]['lat'] = lat
                dict[t]['lon'] = lon
                dict[t]['vel'] = vel
                dict[t]['theta'] = theta
                continue

        self.dict = dict
        print("loading")

        return dict

    def get_vels(self, t1=-1, t2=-1):
        dict = self.dict
        ts = sorted(dict.keys())
        vs, ts2, vel = [], [], 0
        for t in ts:
            d = dict[t]
            vel = d['vel'] if 'vel' in d else vel

            if t1 == -1 or t1 <= t - ts[0] <= t2:
                vs.append(vel)
                ts2.append(t - ts[0])

        return vs, ts2
    

    def haversine_distance(self, lat1, lon1, lat2, lon2):
        # 地球の半径（単位：km）
        radius = 6371.0

        # 緯度・経度をラジアンに変換
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # 差分の計算
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        # Haversine formula の計算
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = radius * c

        return distance

    def get_3d(self, t1=-1, t2=-1):
        print('extract 3d information ... ')
        dict = self.dict
        ts = sorted(dict.keys())
        xs, ys, zs, vs, modes, ts2,thetas = [], [], [], [], [], [], []
        mode, alt, vel, theta = 0, 0, 0, 0

        total_distance = 0
        previous_lat = None
        previous_lon = None

        transformer = Transformer.from_crs('epsg:4612', 'epsg:2451')
        for t in ts:
            d = dict[t]
            lat = [d['lat']]
            lon = [d['lon']]
            alt = d['alt'] if 'alt' in d else alt
            vel = d['vel'] if 'vel' in d else vel
            mode = d['mode'] if 'mode' in d else mode
            theta = d['theta'] if 'theta' in d else theta

            if t1 == -1 or t1 <= t - ts[0] <= t2:
                y, x = transformer.transform(lat, lon)
                xs.append(x)
                ys.append(y)
                zs.append(alt)
                vs.append(vel)
                modes.append(mode)
                ts2.append(t - ts[0])
                thetas.append(theta)

                if previous_lat is not None and previous_lon is not None:
                    distance = self.haversine_distance(previous_lat, previous_lon, lat[0], lon[0])
                    total_distance += distance

                previous_lat = lat[0]
                previous_lon = lon[0]

        #print(f'xs min:{min(xs)} max:{max(xs)} ys min:{min(ys)} ys max:{max(ys)}')
        #print(f"移動した距離は {total_distance:.4f} kmです。")
        return xs, ys, zs, vs, modes, ts2, thetas, total_distance

class Logger(threading.Thread):
    def __init__(self, p_rtk, log_prefix):
        threading.Thread.__init__(self)
        self.daemon = True
        self.kill = False
        self.p_rtk = p_rtk
        d = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
        self.logfile = f'{log_prefix}-{d.year}-{d.month:02d}-{d.day:02d}-{d.hour:02d}-{d.minute:02d}-{d.second:02d}.nmea'
        self.t, self.lat, self.lon, self.mode, self.alt, self.vel, self.theta = 0, 0, 0, 0, 0, 0, 0

    def run(self):
        with open(self.logfile, 'w') as f:
            while not self.kill:
                line = self.p_rtk.stdout.readline()
                line = line.decode()
                if line[3:6] == 'GGA':
                    r = NMEA.parse_GGA(line)
                    if r:
                        self.t, self.lat, self.lon, self.mode, self.alt = r
                elif line[3:6] == 'RMC':
                    r = NMEA.parse_RMC(line)
                    if r:
                        self.t, self.lat, self.lon, self.vel, self.theta = r

                f.write(line)

class RTK:
    base_hosei = 'guest:guest@133.25.86.45:443/HOSEI-F9P'
    base_cq = 'guest:guest@160.16.134.72:80/CQ-F9P'
    str2str = '/home/autoware/shared_dir/RTKLIB-b34d/app/consapp/str2str/gcc/str2str'

    def __init__(self, rover_to, rover_from, base, log_prefix, str2str, info=None):
        self.rover_to = rover_to
        self.rover_from = rover_from
        self.base = base
        self.log_prefix = log_prefix
        self.str2str = str2str
        self.info = info if info is not None else self.info_default
        self.th_logger = None

    def info_default(self, msg):
        print(msg, end='')

    def connect_base(self):
        self.info(f'connecting {self.base} to {self.rover_to}\n')

        cmd = f'exec {self.str2str} -in ntrip://{self.base} -out serial://{self.rover_to}'
        self.info(cmd + '\n')
        self.p_base = subprocess.Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
        for i in range(3):
            line = self.p_base.stderr.readline()
            if line is not None:
                self.info(line)
        self.info(f'connection established.\n')

    def disconnect_base(self):
        self.p_base.kill()
        self.info(f'base station disconnected.\n')

    def start(self):
        self.info(f'start GNSS positioning.\n')

        port, bps = self.rover_from.split(':')
        cmd = f'exec cu -s {bps} -l /dev/{port}'
        self.info(cmd + '\n')
        self.p_rtk = subprocess.Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        self.th_logger = Logger(self.p_rtk, self.log_prefix)
        self.th_logger.start()

    def get_status(self):
        logger = self.th_logger
        if logger is None:
            return None
        return logger.t, logger.lat, logger.lon, logger.mode, logger.alt, logger.vel, logger.theta

    def stop(self):
        self.th_logger.kill = True
        self.th_logger.join()
        self.th_logger = None

        self.p_rtk.stdin.write('~.'.encode())
        time.sleep(1)
        self.p_rtk.kill()

        self.info(f'stop GNSS positioning.\n')


