"""Last.fm 태그 정규화: 표기 통일(alias) + 비장르 태그 제거(drop).

analyze_liked_songs.py 와 generate_report.py 가 공용으로 사용한다.
"""

# 같은 장르의 다른 표기 → 대표 표기로 통일
ALIAS = {
    # hip-hop 계열
    "hip hop": "hip-hop",
    "hiphop": "hip-hop",
    "rap": "hip-hop",
    "korean hip-hop": "k-hip-hop",
    "korean hip hop": "k-hip-hop",
    "k-hiphop": "k-hip-hop",
    "khiphop": "k-hip-hop",
    # k- 계열
    "kpop": "k-pop",
    "k pop": "k-pop",
    "korean pop": "k-pop",
    "korean indie": "k-indie",
    "korean rock": "k-rock",
    "korean ballad": "ballad",
    "korean r&b": "r&b",
    # j- 계열
    "jpop": "j-pop",
    "j pop": "j-pop",
    "japanese pop": "j-pop",
    "jrock": "j-rock",
    "japanese rock": "j-rock",
    "japanese indie": "j-indie",
    # 표기 변형
    "rnb": "r&b",
    "r'n'b": "r&b",
    "rhythm and blues": "r&b",
    "electronica": "electronic",
    "dreampop": "dream pop",
    "post rock": "post-rock",
    "postrock": "post-rock",
    "singer songwriter": "singer-songwriter",
    "alt rock": "alternative rock",
    "alt-rock": "alternative rock",
    "indie-rock": "indie rock",
    "indie-pop": "indie pop",
    "synth pop": "synthpop",
    "synth-pop": "synthpop",
    "lo fi": "lo-fi",
    "lofi": "lo-fi",
}

# 장르가 아닌 태그(국가·연대·성별·감상 속성)는 제거
DROP = {
    # 국가/지역
    "korean", "korea", "japanese", "japan", "british", "uk", "american", "usa",
    "english", "swedish", "french", "german", "chinese", "taiwanese", "thai",
    "asian", "scandinavian", "irish", "canadian", "australian",
    # 연대
    "2020s", "2010s", "2000s", "90s", "80s", "70s", "60s", "1990s", "1980s",
    # 성별/구성 속성
    "female vocalists", "female vocalist", "male vocalists", "male vocalist",
    "girl group", "girl groups", "boy group", "boy groups", "female fronted",
    "duo", "trio", "band", "solo",
    # 기타 비장르
    "seen live", "favorites", "favourites", "korean female solo",
    "4th gen k-pop", "3rd gen k-pop", "soundtrack covers",
}


def normalize(genres: list[str] | set[str]) -> set[str]:
    """태그 목록을 정규화된 장르 집합으로 변환."""
    out: set[str] = set()
    for g in genres:
        g = g.strip().lower()
        g = ALIAS.get(g, g)
        if g and g not in DROP:
            out.add(g)
    return out
