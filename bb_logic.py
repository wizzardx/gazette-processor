#!/bin/env python

import json
from pathlib import Path

from icecream import ic
from typeguard import typechecked

from src.ongoing_convo_with_bronn_2025_06_10.utils import (
    MajorType,
    Notice,
    get_notice_for_gg_num,
)

notice = get_notice_for_gg_num(52724)

print("JUTA'S WEEKLY STATUTES BULLETIN")
print()
print(
    "(Bulletin 21 of 2025 based on Gazettes received during the week 16 to 23 May 2025)"
)
print()
print("JUTA'S WEEKLY E-MAIL SERVICE")
print()

# eg major: PROCLAMATIONS AND NOTICES
# eg minor: Department of Sports, Arts and Culture:
# /type_major, type_minor = get_notice_type_info(notice.gen_n_num)

print(f"ISSN {notice.issn_num}")


@typechecked
def to_bb_header_str(t: MajorType) -> str:
    return {MajorType.GENERAL_NOTICE: "PROCLAMATIONS AND NOTICES"}[t]

    # Note: List of all of the abbreviations can be found in the footer of the docs
    #       that Bronnwyn gave me


print()
# print("PROCLAMATIONS AND NOTICES")
print(to_bb_header_str(notice.type_major))
print()
# print("Department of Sports, Arts and Culture:")
print(f"{notice.type_minor}:")
print()

# print(f"Draft National Policy Framework for Heritage Memorialisation published for comment (GenN 3228 in GG 52724 of 23 May 2025) (p3)")


@typechecked
def get_notice_type_abbr(t: MajorType) -> str:
    ic(t)
    return {
        MajorType.GENERAL_NOTICE: "GenN",
        MajorType.GOVERNMENT_NOTICE: "GN",
        MajorType.BOARD_NOTICE: "BN",
    }[t]

    # Note: List of all of the abbreviations can be found in the footer of the docs
    #       that Bronnwyn gave me


notice_type_major_abbr = get_notice_type_abbr(notice.type_major)

print(
    f"{notice.text}\n({notice_type_major_abbr} {notice.gen_n_num} in GG {notice.gg_num} of {notice.monthday_num} {notice.month_name} {notice.year}) (p{notice.page})"
)

print()


@typechecked
def _compare_against_json_serialization(gg_num: int, notice: Notice):
    j = json.loads(notice.model_dump_json())

    # If a cached version of the json (keyed by gg number) exists in our cache
    # directory, then load and compare against that version, otherwise make
    # a new cache file to use next time
    cache_dir = Path("cache")
    cache_file = cache_dir / f"gg{gg_num}_notice.json"

    if cache_file.exists():
        # Load the cached version
        with open(cache_file, "r") as f:
            cached_notice = json.load(f)

        # Compare the current notice with the cached version
        if j != cached_notice:
            print(f"WARNING: Notice for GG {gg_num} has changed since last cache!")
            print(f"Cached: {cached_notice}")
            print(f"Current: {j}")
        else:
            print(f"Notice for GG {gg_num} matches cached version.")
    else:
        # Create the cache file for next time
        cache_dir.mkdir(exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump(j, f, indent=2)
        print(f"Created cache file for GG {gg_num} at {cache_file}")


@typechecked
def print_notice_info(gg_num: int) -> None:
    notice = get_notice_for_gg_num(gg_num)
    notice_type_major_abbr = get_notice_type_abbr(notice.type_major)
    # print("Department of Tourism:")

    # print("Department of Sports, Arts and Culture:")
    print(f"{notice.type_minor}:")
    print()

    # print("National Astro-Tourism Strategy published for implementation")

    print(
        f"{notice.text}\n({notice_type_major_abbr} {notice.gen_n_num} in GG {notice.gg_num} of {notice.monthday_num} {notice.month_name} {notice.year}) (p{notice.page})"
    )

    print()

    # Next, compare the notice gainst a previous JSON serialization of the
    # record, if that exists.
    _compare_against_json_serialization(gg_num, notice)


print_notice_info(52725)  # Department of Tourism
print_notice_info(52726)  # Department of Transport

# CURRENCY AND EXCHANGES ACT 9 OF 1933
print_notice_info(52695)

# MAGISTRATES' COURTS ACT 32 OF 1944
print_notice_info(52723)

# SUBDIVISION OF AGRICULTURAL LAND ACT 70 OF 1970
print_notice_info(52712)

# # PHARMACY ACT 53 OF 1974
# print_notice_info(52709)
