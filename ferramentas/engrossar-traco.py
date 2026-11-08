# Na Bucha · Design: deixa o traço de uma página de colorir gerada por IA pronto para impressão A4.
# Uso: python3 engrossar-traco.py entrada.jpg saida.png [espessura=5]
# Amplia 3x, limpa cinzas, engrossa o traço de forma uniforme e suaviza as bordas.
import sys, cv2, numpy as np
ent, sai = sys.argv[1], sys.argv[2]
k = int(sys.argv[3]) if len(sys.argv) > 3 else 5
im = cv2.imread(ent, 0)
up = cv2.resize(im, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
tinta = (up < 150).astype(np.uint8) * 255
tinta = cv2.dilate(tinta, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
tinta = cv2.GaussianBlur(tinta, (0, 0), 1.6); tinta = np.where(tinta > 110, 255, 0).astype(np.uint8)
tinta = cv2.GaussianBlur(tinta, (0, 0), 0.9)
out = 255 - tinta
h, w = out.shape; m = int(w * 0.01)
cv2.imwrite(sai, out[m:h - m, m:w - m])
