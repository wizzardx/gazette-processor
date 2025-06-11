#!/bin/env python

from pathlib import Path

from icecream import ic
from typeguard import typechecked

from src.ongoing_convo_with_bronn_2025_06_10.utils import (
    MajorType,
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
    return {MajorType.GENERAL_NOTICE: "GenN", MajorType.GOVERNMENT_NOTICE: "GN"}[t]


notice_type_major_abbr = get_notice_type_abbr(notice.type_major)

print(
    f"{notice.text} ({notice_type_major_abbr} {notice.gen_n_num} in GG {notice.gg_num} of {notice.monthday_num} {notice.month_name} {notice.year}) (p{notice.page})"
)

print()


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


print_notice_info(52725)  # Department of Tourism
# print_notice_info(52726)  # Department of Transport
#
# # CURRENCY AND EXCHANGES ACT 9 OF 1933
# print_notice_info(52695)
#
# # MAGISTRATES' COURTS ACT 32 OF 1944
# print_notice_info(52723)
#
# # # SUBDIVISION OF AGRICULTURAL LAND ACT 70 OF 1970
# # print_notice_info(52712)
