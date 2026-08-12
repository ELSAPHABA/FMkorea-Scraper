from __future__ import annotations

from hypothesis import strategies as st


header_names = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll"), min_codepoint=65, max_codepoint=122),
    min_size=1,
    max_size=16,
).filter(lambda value: value.lower() not in {"referer"})

header_values = st.text(
    alphabet=st.characters(blacklist_characters="\r\n\0"),
    min_size=0,
    max_size=40,
)

headers = st.dictionaries(header_names, header_values, max_size=5)

user_agents = st.lists(
    st.text(alphabet=st.characters(blacklist_characters="\r\n\0"), min_size=1, max_size=80).filter(str.strip),
    min_size=1,
    max_size=8,
)

proxy_hosts = st.builds(
    lambda host, port: f"{host}.example.com:{port}",
    st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=12),
    st.integers(min_value=1, max_value=65535),
)

secret_values = st.one_of(
    st.just("password=super-secret"),
    st.just("cookie: session=abc"),
    st.just("Authorization: bearer token"),
)
