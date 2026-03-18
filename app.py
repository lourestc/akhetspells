import pickle
import math
import streamlit as st
from akhetspells import Spell, Spellbook

LIBRARY_PATH = "Papiros Imperiais de Akhetmun-Heh.bin"

FILTER_FIELDS = [
    "name", "name not",
    "description", "description not",
    "school", "school not",
    "duration", "duration not",
    "range", "range not",
    "area", "area not",
    "save", "save not",
    "target", "target not",
]


@st.cache_resource
def load_library():
    with open(LIBRARY_PATH, "rb") as f:
        return pickle.load(f)


def get_classes(library):
    return sorted({c for s in library for c in s.levels})


def get_schools(library):
    return sorted({s.schools for s in library if s.schools})


def build_spellbook(library, cls, maxlevel, forbidden_schools):
    sb = Spellbook(library, cls, maxlevel)
    for school in forbidden_schools:
        sb.filter_forbidden_school(school)
    return sb


def compute_stats(spells, cls):
    pages = sum(max(int(s.level(cls)), 1) for s in spells)
    cost = sum(
        5 if int(s.level(cls)) == 0 else 10 * int(s.level(cls)) ** 2
        for s in spells
    )
    return pages, cost


def spell_url(spell):
    if spell.url:
        return spell.url
    return (
        "https://cse.google.com/cse?cx=006680642033474972217%3A6zo0hx_wle8&q="
        + "+".join(spell.name.split())
    )


def init_state():
    if "filters" not in st.session_state:
        st.session_state.filters = []
    if "forbidden_schools" not in st.session_state:
        st.session_state.forbidden_schools = []


def render_sidebar(library):
    st.sidebar.title("Spellbook Setup")

    classes = get_classes(library)
    cls = st.sidebar.selectbox("Class", classes, index=classes.index("wizard") if "wizard" in classes else 0)
    maxlevel = st.sidebar.selectbox("Max Level", list(range(10)), index=6)

    st.sidebar.divider()
    st.sidebar.subheader("Forbidden Schools")

    schools = get_schools(library)
    forbidden = st.session_state.forbidden_schools

    for i, school in enumerate(forbidden):
        col1, col2 = st.sidebar.columns([4, 1])
        col1.markdown(f"~~{school}~~")
        if col2.button("×", key=f"rm_school_{i}"):
            st.session_state.forbidden_schools.pop(i)
            st.rerun()

    available = [s for s in schools if s not in forbidden]
    if available:
        col1, col2 = st.sidebar.columns([4, 1])
        new_school = col1.selectbox("Add school", available, label_visibility="collapsed", key="new_school_select")
        if col2.button("+", key="add_school"):
            st.session_state.forbidden_schools.append(new_school)
            st.rerun()

    return cls, maxlevel


def render_filter_bar():
    st.subheader("Filters")

    filters = st.session_state.filters

    # Active filter chips
    if filters:
        cols = st.columns(len(filters) + 1)
        for i, (field, query) in enumerate(filters):
            with cols[i]:
                st.markdown(f"`{field}: {query}`")
                if st.button("×", key=f"rm_filter_{i}"):
                    st.session_state.filters.pop(i)
                    st.rerun()

    # Add filter row
    col1, col2, col3 = st.columns([2, 3, 1])
    with col1:
        field = st.selectbox("Field", FILTER_FIELDS, label_visibility="collapsed", key="filter_field")
    with col2:
        query = st.text_input("Query", label_visibility="collapsed", placeholder="search term...", key="filter_query")
    with col3:
        if st.button("+ Add", key="add_filter"):
            if query.strip():
                st.session_state.filters.append([field, query.strip()])
                st.rerun()


def render_results(spells, cls):
    pages, cost = compute_stats(spells, cls)

    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Spells", len(spells))
    col2.metric("Pages", pages)
    col3.metric("Cost", f"{int(cost):,} gp")

    if not spells:
        st.info("No spells match the current filters.")
        return None

    rows = [
        {"Level": s.level(cls), "Name": s.name, "Edition": s.edition or ""}
        for s in spells
    ]

    import pandas as pd
    df = pd.DataFrame(rows)

    selection = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key="spell_table",
    )

    selected_rows = selection.selection.rows
    if selected_rows:
        return spells[selected_rows[0]]
    return None


def render_spell_detail(spell, cls):
    st.divider()
    st.subheader(spell.name)

    def field_row(label, value):
        if value:
            st.markdown(f"**{label}:** {value}")

    col1, col2 = st.columns(2)
    with col1:
        field_row("Level", spell.level(cls))
        field_row("School", spell.schools)
        if spell.subschools:
            field_row("Subschool", ", ".join(spell.subschools))
        if spell.descriptors:
            field_row("Descriptor", ", ".join(spell.descriptors))
        field_row("Components", ", ".join(spell.components) if spell.components else None)
        field_row("Casting Time", spell.castingtime)
    with col2:
        field_row("Range", spell.range)
        field_row("Target", spell.target)
        field_row("Effect", spell.effect)
        field_row("Area", spell.area)
        field_row("Duration", spell.duration)
        field_row("Saving Throw", spell.saving)
        field_row("Spell Resistance", spell.SR)

    field_row("Source", spell.source)
    st.link_button("Open Reference", spell_url(spell))

    if spell.description:
        st.divider()
        st.markdown(spell.description)


def main():
    st.set_page_config(page_title="AkhetSpells", page_icon="📜", layout="wide")
    st.title("📜 AkhetSpells")

    init_state()

    library = load_library()
    cls, maxlevel = render_sidebar(library)

    sb = build_spellbook(library, cls, maxlevel, st.session_state.forbidden_schools)
    results = sb.search_spells(st.session_state.filters) if st.session_state.filters else sb.spells

    render_filter_bar()
    selected_spell = render_results(results, cls)

    if selected_spell:
        render_spell_detail(selected_spell, cls)


if __name__ == "__main__":
    main()
