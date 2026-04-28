"""Sample data and helpers for reading-domain tests.

These can't live in conftest.py because Python doesn't auto-import constants
from conftest — only pytest fixtures get auto-discovery. Tests that need
these imports do:

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _sample_data import SAMPLE_ARXIV_XML, make_alphaxiv_html
"""
import textwrap


# COPY VERBATIM from tests/lib/conftest.py — preserve all keys, values, formatting:
SAMPLE_CONFIG = {
    "vault_path": "/tmp/test-vault",
    "language": "mixed",
    "research_domains": {
        "coding-agent": {
            "keywords": ["coding agent", "code generation", "code repair"],
            "arxiv_categories": ["cs.AI", "cs.SE", "cs.CL"],
            "priority": 5,
        },
        "rl-for-code": {
            "keywords": ["RLHF", "reinforcement learning", "reward model"],
            "arxiv_categories": ["cs.LG", "cs.AI"],
            "priority": 4,
        },
    },
    "excluded_keywords": ["survey", "3D"],
    "scoring_weights": {
        "keyword_match": 0.4,
        "recency": 0.2,
        "popularity": 0.3,
        "category_match": 0.1,
    },
}


# COPY VERBATIM SAMPLE_ARXIV_XML from tests/lib/conftest.py — preserve the entire XML body:
SAMPLE_ARXIV_XML = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2406.12345v1</id>
        <title>A Coding Agent for Code Generation</title>
        <summary>This paper presents a novel coding agent for code generation using reinforcement learning.</summary>
        <published>2026-03-10T00:00:00Z</published>
        <author><name>Alice Smith</name></author>
        <author><name>Bob Jones</name></author>
        <arxiv:primary_category term="cs.AI"/>
        <category term="cs.AI"/>
        <category term="cs.CL"/>
      </entry>
      <entry>
        <id>http://arxiv.org/abs/2406.67890v1</id>
        <title>Reward Model Training with RLHF</title>
        <summary>We present a reward model trained with RLHF for code repair tasks.</summary>
        <published>2026-03-12T00:00:00Z</published>
        <author><name>Charlie Lee</name></author>
        <arxiv:primary_category term="cs.LG"/>
        <category term="cs.LG"/>
        <category term="cs.AI"/>
      </entry>
    </feed>
""")


# COPY VERBATIM SAMPLE_SSR_PAPER from tests/lib/conftest.py:
SAMPLE_SSR_PAPER = {
    "id": "2603.12228",
    "title": "Neural Code Agent",
    "abstract": "A coding agent with code generation capabilities.",
    "votes": 39,
    "visits": 1277,
    "published": "2026-03-12T17:49:30.000Z",
    "topics": ["Computer Science", "cs.AI", "cs.LG"],
    "authors": ["Alice"],
}


# COPY VERBATIM make_alphaxiv_html function body from tests/lib/conftest.py:
def make_alphaxiv_html(papers: list[dict] | None = None) -> str:
    """Build minimal HTML mimicking alphaXiv's TanStack Router SSR format."""
    if papers is None:
        papers = [SAMPLE_SSR_PAPER]
    parts = ["<html><head></head><body><script>"]
    for i, p in enumerate(papers):
        pid = p["id"]
        topics_str = ",".join(f'"{t}"' for t in p.get("topics", []))
        authors_str = ",".join(f'"{a}"' for a in p.get("authors", []))
        parts.append(f'title:"{p.get("title", "")}",abstract:"{p.get("abstract", "")}",')
        parts.append(f'image_url:"image/{pid}v1.png",universal_paper_id:"{pid}",')
        parts.append(
            f"metrics:$R[{100+i*10}]={{visits_count:$R[{101+i*10}]="
            f"{{all:{p.get('visits', 0)},last_7_days:{p.get('visits', 0)}}},"
            f"total_votes:{p.get('votes', 0)},public_total_votes:{p.get('votes', 0) * 2}}},"
        )
        parts.append(f'first_publication_date:"{p.get("published", "2026-03-12T00:00:00.000Z")}",')
        parts.append(f"topics:$R[{102+i*10}]=[{topics_str}],")
        parts.append(f"authors:$R[{103+i*10}]=[{authors_str}],")
    parts.append("</script></body></html>")
    return "".join(parts)
