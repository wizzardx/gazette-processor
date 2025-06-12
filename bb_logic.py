#!/bin/env python

import json
from pathlib import Path

from typeguard import typechecked

from src.ongoing_convo_with_bronn_2025_06_10.cached_llm import CachedLLM
from src.ongoing_convo_with_bronn_2025_06_10.utils import (
    MajorType,
    Notice,
    get_notice_for_gg_num,
)

cached_llm = CachedLLM()

notice = get_notice_for_gg_num(
    gg_number=52724, notice_number=3228, cached_llm=cached_llm
)


print("# **JUTA'S WEEKLY STATUTES BULLETIN**")

print()
print(
    "##### (Bulletin 21 of 2025 based on Gazettes received during the week 16 to 23 May 2025)"
)
print()
print("## JUTA'S WEEKLY E-MAIL SERVICE")
print()

# eg major: PROCLAMATIONS AND NOTICES
# eg minor: Department of Sports, Arts and Culture:
# /type_major, type_minor = get_notice_type(notice.gen_n_num)

print(f"*ISSN {notice.issn_num}*")


@typechecked
def to_bb_header_str(t: MajorType) -> str:
    return {MajorType.GENERAL_NOTICE: "PROCLAMATIONS AND NOTICES"}[t]

    # Note: List of all of the abbreviations can be found in the footer of the docs
    #       that Bronnwyn gave me


print()
# print("PROCLAMATIONS AND NOTICES")
to_bb_header_str = to_bb_header_str(notice.type_major)
print(f"## **{to_bb_header_str}**")
print()
# print("Department of Sports, Arts and Culture:")
print(f"### **{notice.type_minor}**")
print()


# print(f"Draft National Policy Framework for Heritage Memorialisation published for comment (GenN 3228 in GG 52724 of 23 May 2025) (p3)")


@typechecked
def get_notice_type_abbr(t: MajorType) -> str:
    # ic(t)
    return {
        MajorType.GENERAL_NOTICE: "GenN",
        MajorType.GOVERNMENT_NOTICE: "GN",
        MajorType.BOARD_NOTICE: "BN",
    }[t]

    # Note: List of all of the abbreviations can be found in the footer of the docs
    #       that Bronnwyn gave me


notice_type_major_abbr = get_notice_type_abbr(notice.type_major)

print(
    f"{notice.text}\n\n({notice_type_major_abbr} {notice.gen_n_num} in GG {notice.gg_num} of {notice.monthday_num} {notice.month_name} {notice.year}) (p{notice.page})"
)

print()


@typechecked
def _compare_against_json_serialization(gg_number: int, notice: Notice):
    j = json.loads(notice.model_dump_json())

    # If a cached version of the json (keyed by gg number) exists in our cache
    # directory, then load and compare against that version, otherwise make
    # a new cache file to use next time
    cache_dir = Path("cache")
    cache_file = cache_dir / f"gg{gg_number}_notice.json"

    if cache_file.exists():
        # Load the cached version
        with open(cache_file, "r") as f:
            cached_notice = json.load(f)

        # Compare the current notice with the cached version
        if j != cached_notice:
            print(f"WARNING: Notice for GG {gg_number} has changed since last cache!")
            print(f"Cached: {cached_notice}")
            print(f"Current: {j}")
            # assert 0
        else:
            print(f"Notice for GG {gg_number} matches cached version.")
    else:
        # Create the cache file for next time
        cache_dir.mkdir(exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(j, f, indent=2)
        print(f"Created cache file for GG {gg_number} at {cache_file}")


@typechecked
def print_notice_info(
    gg_number: int, notice_number: int, cached_llm: CachedLLM
) -> None:
    notice = get_notice_for_gg_num(
        gg_number=gg_number, notice_number=notice_number, cached_llm=cached_llm
    )
    notice_type_major_abbr = get_notice_type_abbr(notice.type_major)
    # print("Department of Tourism:")

    # print("Department of Sports, Arts and Culture:")
    type_minor = notice.type_minor

    # Only bring the later ones to uppercase:
    if type_minor not in {"Department of Tourism", "Department of Transport"}:
        type_minor = type_minor.upper()

    print(f"### **{type_minor}**")
    print()

    # print("National Astro-Tourism Strategy published for implementation")\
    print(
        f"{notice.text}\n\n({notice_type_major_abbr} {notice.gen_n_num} in GG {notice.gg_num} of {notice.monthday_num} {notice.month_name} {notice.year}) (p{notice.page})"
    )

    print()

    # Next, compare the notice gainst a previous JSON serialization of the
    # record, if that exists.
    # _compare_against_json_serialization(gg_number=gg_number, notice=notice)


def print_notice(notice_number: int, gg_number: int) -> None:
    print_notice_info(
        notice_number=notice_number, gg_number=gg_number, cached_llm=cached_llm
    )


# Department of Tourism
print_notice(3229, 52725)

# Department of Transport:
print_notice(6220, 52726)

# CURRENCY AND EXCHANGES ACT 9 OF 1933
print_notice(3197, 52695)

# MAGISTRATES' COURTS ACT 32 OF 1944
print_notice(6219, 52723)

# SUBDIVISION OF AGRICULTURAL LAND ACT 70 OF 1970
print_notice(6214, 52712)

# PHARMACY ACT 53 OF 1974
print_notice(787, 52709)

# COMPENSATION FOR OCCUPATIONAL INJURIES AND DISEASES ACT 130 OF 1993
print_notice(3200, 52699)
print_notice(3227, 52722)

# ROAD ACCIDENT FUND ACT 56 OF 1996
print_notice(786, 52691)

# # SPECIAL INVESTIGATING UNITS AND SPECIAL TRIBUNALS ACT 74 OF 1996
# print_notice(260, 52705)
