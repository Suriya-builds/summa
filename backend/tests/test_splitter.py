import json

import pytest

from app.services.splitter import ImportFormatError, parse_text, parse_upload


def test_one_message_per_line_with_sender_prefix():
    msgs = parse_text("VM-HDFCBK: Sent Rs.250.00 From HDFC Bank A/C *1234 To SWIGGY\nAD-SBIUPI: Dear UPI user A/C X1234 debited by 120.0")
    assert [m.sender for m in msgs] == ["VM-HDFCBK", "AD-SBIUPI"]


def test_pipe_format_reads_date():
    msgs = parse_text("VM-HDFCBK | 2026-10-03 14:22 | Sent Rs.250.00 From HDFC Bank A/C *1234 To SWIGGY")
    assert msgs[0].received_at.hour == 14


def test_csv_and_json():
    csv_text = "sender,date,body\nVM-HDFCBK,2026-10-03 10:00,Sent Rs.250.00 From HDFC Bank A/C *1234 To SWIGGY"
    assert parse_upload("a.csv", csv_text)[0].sender == "VM-HDFCBK"
    js = json.dumps([{"address": "VM-HDFCBK", "date": 1759480330000, "body": "Sent Rs.250.00 From HDFC Bank A/C *1234 To SWIGGY"}])
    assert parse_upload("a.json", js)[0].received_at.year == 2025


def test_xml_backup_keeps_only_received():
    xml = '<smses><sms address="VM-HDFCBK" date="1759480330000" type="1" body="Sent Rs.250.00 From HDFC A/C *1234 To SWIGGY"/>' \
          '<sms address="me" date="1759480330000" type="2" body="outgoing text message here"/></smses>'
    assert len(parse_upload("backup.xml", xml)) == 1


def test_xml_entities_rejected():
    with pytest.raises(ImportFormatError):
        parse_upload("x.xml", '<!DOCTYPE x [<!ENTITY a "b">]><smses/>')


def test_csv_without_body_column():
    with pytest.raises(ImportFormatError):
        parse_upload("a.csv", "foo,bar\n1,2")
