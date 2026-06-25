# -*- coding: utf-8 -*-
"""
OAK / DepthAI barcode & DataMatrix reader

Architecture :
  OAK (on-device)
    Camera (1920x1080)
      -> Stage 1 : YOLOv8 détection étiquette
      -> Script node : extrait les ROI des détections
      -> ImageManip  : crop + resize du ROI
      -> XLinkOut    : envoie uniquement le crop au host

  Host
    QrDecode  : reçoit le crop -> zxingcpp -> mutex
    PrintThread : CSV horodaté (inchangé vs Data_Matrix_Reader_2_CSV.py)

Prérequis :
    pip install depthai>=3.0 zxingcpp opencv-python
    Modèle : label_detector.tar.xz (YOLOv8 converti en superblob via HubAI)
"""

import csv
import threading
import numpy as np
import cv2
import zxingcpp
import depthai as dai
from datetime import date, datetime

# ── Globals ──────────────────────────────────────────────────────────────────
my_mutex   = threading.Lock()
data       = None
keep_going = True


# ── PrintThread (identique à Data_Matrix_Reader_2_CSV.py) ────────────────────
class PrintThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global data, keep_going, my_mutex
        previous_data = ''
        while keep_going:
            today  = date.today().strftime("%Y-%m-%d")
            timeRN = datetime.now().strftime("%H:%M:%S")
            with my_mutex:
                to_publish_data = data
            if to_publish_data and previous_data != to_publish_data:
                print(f"Nouveau scan : {to_publish_data} | {today} {timeRN}")
                previous_data = to_publish_data
                filename = today + '_Database.csv'
                with open(filename, mode='a') as csvfile:
                    writer = csv.writer(csvfile, delimiter=',',
                                        quotechar='"', quoting=csv.QUOTE_ALL)
                    writer.writerow([to_publish_data + ', ' + today + '_' + timeRN])


# ── QrDecode : pipeline DepthAI + crop on-device + décodage host ─────────────
class QrDecode(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global data, keep_going, my_mutex

        with dai.Pipeline() as pipeline:

            # ── Caméra 1920x1080 ─────────────────────────────────────────────
            cam = pipeline.create(dai.node.Camera).build()
            rgb = cam.requestOutput((1920, 1080), dai.ImgFrame.Type.BGR888p)

            # ── Stage 1 : détection étiquette (YOLOv8 superblob) ─────────────
            det_nn = pipeline.create(dai.node.DetectionNetwork)
            det_nn.setNNArchive(dai.NNArchive("label_detector.tar.xz"))
            det_nn.setConfidenceThreshold(0.5)
            rgb.link(det_nn.input)

            # ── Script node : ROI → config ImageManip ────────────────────────
            script = pipeline.create(dai.node.Script)
            script.setScript("""
import depthai as dai

while True:
    dets  = node.io['dets'].get()
    frame = node.io['frame'].get()

    for det in dets.detections:
        # Marge 5% autour du bbox pour éviter les coupures
        margin = 0.05
        xmin = max(0.0, det.xmin - margin)
        ymin = max(0.0, det.ymin - margin)
        xmax = min(1.0, det.xmax + margin)
        ymax = min(1.0, det.ymax + margin)

        cfg = dai.ImageManipConfig()
        cfg.setCropRect(xmin, ymin, xmax, ymax)
        cfg.setResize(640, 480)
        cfg.setKeepAspectRatio(True)

        node.io['manip_cfg'].send(cfg)
        node.io['manip_img'].send(frame)
""")
            det_nn.out.link(script.inputs['dets'])
            rgb.link(script.inputs['frame'])

            # ── ImageManip : crop on-device ───────────────────────────────────
            manip = pipeline.create(dai.node.ImageManip)
            manip.setWaitForConfigInput(True)
            manip.setMaxOutputFrameSize(640 * 480 * 3)
            script.outputs['manip_cfg'].link(manip.inputConfig)
            script.outputs['manip_img'].link(manip.inputImage)

            # ── XLinkOut : envoie uniquement le crop au host ──────────────────
            xout_crop = pipeline.create(dai.node.XLinkOut)
            xout_crop.setStreamName("crops")
            manip.out.link(xout_crop.input)

            # ── XLinkOut optionnel : frame complète pour prévisualisation ─────
            xout_rgb = pipeline.create(dai.node.XLinkOut)
            xout_rgb.setStreamName("rgb")
            rgb.link(xout_rgb.input)

            # ── Démarrage du pipeline ─────────────────────────────────────────
            pipeline.start()
            q_crop = pipeline.getOutputQueue("crops", maxSize=8, blocking=False)
            q_rgb  = pipeline.getOutputQueue("rgb",   maxSize=4, blocking=False)

            while keep_going:

                # ── Décodage du crop reçu depuis l'OAK ───────────────────────
                if q_crop.has():
                    crop_frame = q_crop.get().getCvFrame()
                    results = zxingcpp.read_barcodes(crop_frame)
                    for result in results:
                        with my_mutex:
                            data = result.text

                        # Dessin du polygone sur le crop
                        pos_str = str(result.position).split(' ')
                        x = [int(p.split('x')[0]) for p in pos_str]
                        y = [int(p.split('x')[1].replace('\x00', '')) for p in pos_str]
                        rect = np.array(list(zip(x, y)), dtype=np.int32)
                        cv2.polylines(crop_frame, [rect], True, (0, 255, 0), 2)
                        cv2.putText(crop_frame, result.text, (x[0], y[0] - 10),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

                    cv2.imshow("Crop étiquette", crop_frame)

                # ── Prévisualisation frame complète (optionnel) ───────────────
                if q_rgb.has():
                    cv2.imshow("OAK - Vue complète", q_rgb.get().getCvFrame())

                if cv2.waitKey(1) == 27:  # ESC pour quitter
                    keep_going = False

        cv2.destroyAllWindows()


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    t1 = QrDecode()
    t1.start()
    t2 = PrintThread()
    t2.start()
    t1.join()
    t2.join()
    print('threads terminés')
