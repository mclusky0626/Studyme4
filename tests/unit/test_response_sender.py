from app.discord.response_sender import split_response_bubbles


def test_explicit_bubble_markers_become_separate_messages():
    result = split_response_bubbles("헐 진짜?[[BUBBLE]]그럼 결과는 언제 나옴")
    assert result == ["헐 진짜?", "그럼 결과는 언제 나옴"]


def test_newlines_also_become_bubble_boundaries():
    result = split_response_bubbles("일단 저장해둘게\n나중에 다시 물어봐")
    assert result == ["일단 저장해둘게", "나중에 다시 물어봐"]


def test_short_answer_stays_as_one_bubble():
    assert split_response_bubbles("ㅇㅇ 알겠음") == ["ㅇㅇ 알겠음"]


def test_long_ignored_marker_response_is_safely_wrapped():
    text = "첫 번째 설명입니다. 두 번째 설명도 있습니다. 세 번째 설명까지 이어집니다."
    result = split_response_bubbles(text, max_chars=25)
    assert len(result) >= 2
    assert all(len(part) <= 50 for part in result)


def test_malformed_brackets_and_unbalanced_bold_are_cleaned():
    result = split_response_bubbles(
        "[[유녀전기 ** 일러스트네.\n[[분위기 ** 엄청 고풍스럽고 멋지다."
    )
    assert result == ["유녀전기 일러스트네.", "분위기 엄청 고풍스럽고 멋지다."]
    assert all("[[" not in part and "**" not in part for part in result)


def test_valid_bold_is_preserved():
    assert split_response_bubbles("이건 **고풍스러운 일러스트** 같아.") == [
        "이건 **고풍스러운 일러스트** 같아."
    ]
