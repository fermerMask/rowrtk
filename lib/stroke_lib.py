import math, sys
from lib.pll_rtk_lib import *
import matplotlib.pyplot as plt

class Stroke:
  @classmethod
  def extract_peaks(self,vs, ts, T=50):
    peaks = [i for i in range(T, len(vs)-1) if (vs[i] < min(vs[i-T:i]) and vs[i] == min(vs[i-T:i+T]))]
   # print(f'peaks num:{len(peaks)} min:{min(peaks)} max:{max(peaks)}')
    return peaks
  
  @classmethod
  def extract_strokes(self, vs, ts, T=50):
    ts = ts
    peaks = self.extract_peaks(vs, ts, T)
    if vs[peaks[0]] > vs[peaks[1]]:
      peaks = peaks[1:]
    
    strokes = []
    i = 0
    for i in range(0, len(peaks) - 2, 2):
      p0, p1, p2 = peaks[i], peaks[i+1], peaks[i+2]
      if vs[p0] < vs[p1] and vs[p1] > vs[p2]:
        strokes.append((p0, p1, p2))
      else:
        break
    
    periods = [ts[p2] - ts[p0] for p0, p1, p2 in strokes]
    if len(periods) == 0:
      mean_period = 0
    else:
      mean_period = sum(periods) / len(periods)
    
    print(f'stroke num:{len(strokes)} mean period:{mean_period:.2f}')

    for p0,p1,p2 in strokes:
      vel = vs[p0:p2]
      time = ts[p0:p2]

    return [(vs[p0:p2], ts[p0:p2]) for p0, p1, p2 in strokes]

def plot_strokes(strokes):
  plt.figure(figsize=(3.2,2.4))
  for vs, ts in strokes:
    ts = [t - ts[0] for t in ts]
    plt.plot(ts, vs)

  plt.xlabel('time[s]')
  plt.ylabel('velocity[m/s]')
  plt.grid()
  plt.show()

def plot_peaks(vs, ts, peaks):
  plt.figure(figsize=(20,10))
  plt.plot(ts, vs)
  plt.scatter([ts[p] for p in peaks], [vs[p] for p in peaks], s=16, color='red')
  plt.xlabel('time[s]')
  plt.ylabel('velocity[m/s]')
  plt.grid()
  plt.title(title)
  plt.savefig(title + '.png')
  plt.show()

def plot_peak_and_alts(vs, ts, peaks, alts, title):
  fig, axes = plt.subplots(2, 1, tight_layout=True)
  axes[0].plot(ts, vs)
  axes[0].scatter([ts[p] for p in peaks], [vs[p] for p in peaks], s=20, color='red')
  axes[1].plot(ts, alts)
  axes[1].scatter([ts[p] for p in peaks], [alts[p] for p in peaks], s=20, color='red')
  axes[0].set_xlabel('time[s]')
  axes[1].set_xlabel('time[s]')
  axes[0].set_ylabel('velocity[m/s]')
  axes[1].set_ylabel('alt[m]')
  axes[0].grid()
  axes[1].grid()
 # plt.savefig(title + '.png')
  plt.show()

def plot_peaks_and_theta(vs,ts,peaks,theta,title):
  fig,axes = plt.subplots(2,1,tight_layout=True)
  axes[0].plot(ts,vs)
  axes[0].scatter([ts[p] for p in peaks], [vs[p] for p in peaks],s=20,color="red")
  axes[1].plot(ts,theta)
  axes[1].scatter([ts[p] for p in peaks], [theta[p] for p in peaks], s=20, color='red')
  axes[1].plot([ts[p] for p in peaks],[theta[p] for p in peaks])
  axes[0].set_xlabel('time[s]')
  axes[1].set_xlabel('time[s]')
  axes[0].set_ylabel('velocity[m/s]')
  axes[1].set_ylabel('theta')
  axes[0].grid()
  axes[1].grid()

  plt.title(title)
  # plt.savefig(title + '.png')
  plt.show()

def plot_stroke_distance(strokes):
  distance = []
  count = 0
  num = []
  for vs,ts in strokes:
    ts = [t - ts[0] for t in ts]
    vs1 = np.array(vs)
    t = np.array(t)
    d = np.trapz(vs1,0.01)
    distance.append(d)
    count += 1
    num.append(count)


def main():
  stroke = Stroke()
  nmea_file = sys.argv[1]
  Tfrom = float(sys.argv[2]) if len(sys.argv) > 2 else -1
  Tto = float(sys.argv[3]) if len(sys.argv) > 3 else -1
  Tw = int(sys.argv[4]) if len(sys.argv) > 4 else 50

  nmea = NMEA()
  nmea.load(nmea_file)
  # vs, ts = nmea.get_vels(Tfrom, Tto)
  xs, ys, zs, vs, modes, ts, theta, distance = nmea.get_3d(Tfrom, Tto)
  print(f'fix rate:{len([mode for mode in modes if mode == 4]) / len(modes):.2f}')

  peaks = stroke.extract_peaks(vs, ts, Tw)
  #plot_peaks(vs, ts, peaks, f'{nmea_file}-peaks-{Tfrom }-{Tto}')
  plot_peak_and_alts(vs, ts, peaks, zs, f'{nmea_file}-peakalt-{Tfrom}-{Tto}')
  plot_peaks_and_theta(vs,ts,peaks,theta,f'peaktheta-{Tfrom}-{Tto}')

  strokes = stroke.extract_strokes(vs, ts, Tw)
  plot_strokes(strokes)
  #plot_stroke_distance(xs,ys,ts,peaks)
  print(f"distance:{distance}")
  
if __name__ == '__main__':
  main()