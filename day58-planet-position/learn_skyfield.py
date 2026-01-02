"""
Day 58: Skyfield学習用スクリプト
ターミナルで実行して惑星の位置計算を学習する
#Skyfieldのトップページにあるプログラムを実行してみる
Skyfield: https://rhodesmill.org/skyfield/
参考記事: 
note 天文と気象（とその他いろいろ）「Skyfieldを使いながら、天球座標系を学ぶ」
https://note.com/symmetrybreaking/n/n74dbbf578fb0
"""


from skyfield.api import load,N,W,wgs84

# 火星の天空上の位置、地心座標
# Create the timescale and ask the current time.
ts = load.timescale()
t = ts.now()

# Load the JPL ephemeris DE421 (covers 1900-2050).
planets = load('de421.bsp')
earth,mars = planets['earth'], planets['mars']

# What's the position of Mars, viewed from earth?
astrometric = earth.at(t).observe(mars)
ra, dec, distance = astrometric.radec()

# 赤経（Right Ascension）と赤緯（Declination）と天文単位（au）
print(ra)
print(dec)
print(distance)
