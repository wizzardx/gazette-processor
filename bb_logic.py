#!/bin/env python

from pathlib import Path

from icecream import ic
from typeguard import typechecked

from src.ongoing_convo_with_bronn_2025_06_10.utils import (
    MajorType,
    get_record_for_gg_num,
)

record = get_record_for_gg_num(52724)

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
# /type_major, type_minor = get_record_type_info(record.gen_n_num)

print(f"ISSN {record.issn_num}")


@typechecked
def to_bb_header_str(t: MajorType) -> str:
    return {MajorType.GENERAL_NOTICE: "PROCLAMATIONS AND NOTICES"}[t]


print()
# print("PROCLAMATIONS AND NOTICES")
print(to_bb_header_str(record.type_major))
print()
# print("Department of Sports, Arts and Culture:")
print(f"{record.type_minor}:")
print()

# print(f"Draft National Policy Framework for Heritage Memorialisation published for comment (GenN 3228 in GG 52724 of 23 May 2025) (p3)")


@typechecked
def get_record_type_abbr(t: MajorType) -> str:
    return {MajorType.GENERAL_NOTICE: "GenN"}[t]


record_type_major_abbr = get_record_type_abbr(record.type_major)

print(
    f"{record.text} ({record_type_major_abbr} {record.gen_n_num} in GG {record.gg_num} of {record.monthday_num} {record.month_name} {record.year}) (p{record.page})"
)

print()

record = get_record_for_gg_num(52725)

print("Department of Tourism:")

print("National Astro-Tourism Strategy published for implementation")
print("(GenN 3229 in GG 52725 of 23 May 2025) (p3)")
