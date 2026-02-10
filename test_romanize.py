from pythainlp.transliterate import romanize
try:
    print(f"Royin: {romanize('มหาวิทยาลัย', engine='royin')}")
except Exception as e:
    print(f"Royin error: {e}")

try:
    print(f"Paiboon: {romanize('สวัสดีครับ', engine='paiboon')}")
except Exception as e:
    print(f"Paiboon error: {e}")

try:
    # check if thai2rom is available
    print(f"Thai2Rom: {romanize('มหาวิทยาลัย', engine='thai2rom')}")
except Exception as e:
    print(f"Thai2Rom error: {e}")
