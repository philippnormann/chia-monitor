def format_plot_count(plot_count: int) -> str:
    return f"🌾 Plot Count: {plot_count}"


def format_plot_size(plot_size: int) -> str:
    return f"🧺 Plot Size: {plot_size/(1024 ** 4):.3f} TiB"


def format_balance(balance: int) -> str:
    return f"💰 Total Balance: {balance/1e12:.5f} XCH"


def format_space(space: int) -> str:
    return f"💾 Current Netspace: {space/(1024 ** 5):.3f} PiB"


def format_diffculty(diffculty: int) -> str:
    return f"📈 Farming Difficulty: {diffculty}"


def format_peak_height(peak_height: int, fix_indent=False) -> str:
    indent = " " * (1 if fix_indent else 0)
    return f"🏔️ {indent}Peak Height: {peak_height}"


def format_synced(synced: int) -> str:
    return f"🔄 Synced: {synced}"


def format_full_node_count(full_node_count: int, node_type="Full Node") -> str:
    return f"📶 {node_type} Peer Count: {full_node_count}"


def format_hostname(hostname: str, fix_indent=False) -> str:
    indent = " " * (1 if fix_indent else 0)
    return f"🖥️ {indent}Host: {hostname}"


def format_challenge_hash(challenge_hash: str) -> str:
    return f"🎰 Challenge Hash: {challenge_hash}"


def format_challenges_per_min(challenges_per_min: float) -> str:
    return f"🎰 Challenges Per Minute: {challenges_per_min:.2f}"


def format_signage_point(signage_point: str) -> str:
    return f"⌛ Signage Point: {signage_point}"


def format_signage_points_per_min(signage_points_per_min: float) -> str:
    return f"⌛ Signage Points Per Minute: {signage_points_per_min:.2f}"


def format_signage_point_index(signage_point_index: int) -> str:
    return f"🔏 Signage Point Index: {signage_point_index}"


def format_passed_filter(passed_filter: int) -> str:
    return f"🔎 Passed Filter: {passed_filter}"


def format_passed_filter_per_min(passed_filter_per_min: float) -> str:
    return f"🔎 Passed Filters Per Minute: {passed_filter_per_min:.2f}"


def format_proofs(proofs: int) -> str:
    return f"✅ Proofs found: {proofs}"
