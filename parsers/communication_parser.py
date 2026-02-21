"""Parser for communication formats: EML, MSG, ICS, VCF."""

import io
import email
from email import policy
import structlog
from parsers.base import BaseParser

logger = structlog.get_logger(__name__)


class CommunicationParser(BaseParser):
    """Handles email and contact/calendar files."""

    @property
    def supported_extensions(self) -> list[str]:
        return [".eml", ".msg", ".ics", ".vcf", ".mhtml", ".mht"]

    def parse(self, file_bytes: bytes, filename: str) -> str:
        ext = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

        if ext == ".eml" or ext == ".mhtml" or ext == ".mht":
            return self._parse_eml(file_bytes, filename)
        elif ext == ".msg":
            return self._parse_msg(file_bytes, filename)
        elif ext == ".ics":
            return self._parse_ics(file_bytes, filename)
        elif ext == ".vcf":
            return self._parse_vcf(file_bytes, filename)
        else:
            return f"[Unsupported communication format: {ext}]"

    def _parse_eml(self, file_bytes: bytes, filename: str) -> str:
        """Extract content from EML file."""
        try:
            msg = email.message_from_bytes(file_bytes, policy=policy.default)
            
            headers = []
            for h in ["From", "To", "Cc", "Subject", "Date"]:
                if msg[h]:
                    headers.append(f"{h}: {msg[h]}")
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_content()
                        break
                    elif part.get_content_type() == "text/html" and not body:
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(part.get_content(), "html.parser")
                        body = soup.get_text(separator="\n", strip=True)
            else:
                body = msg.get_content()

            result = "[Email: " + filename + "]\n"
            result += "\n".join(headers) + "\n\n"
            result += body
            
            logger.info("eml_parsed", filename=filename)
            return result
        except Exception as e:
            logger.error("eml_parse_error", filename=filename, error=str(e))
            return f"[Error extracting EML content: {str(e)}]"

    def _parse_msg(self, file_bytes: bytes, filename: str) -> str:
        """Extract content from Outlook MSG file."""
        try:
            import extract_msg
            msg = extract_msg.Message(file_bytes)
            
            result = "[Outlook Email: " + filename + "]\n"
            result += f"From: {msg.sender}\n"
            result += f"To: {msg.to}\n"
            result += f"Subject: {msg.subject}\n"
            result += f"Date: {msg.date}\n\n"
            result += msg.body
            
            msg.close()
            logger.info("msg_parsed", filename=filename)
            return result
        except ImportError:
            return "[Error: extract-msg library not installed]"
        except Exception as e:
            logger.error("msg_parse_error", filename=filename, error=str(e))
            return f"[Error extracting MSG content: {str(e)}]"

    def _parse_ics(self, file_bytes: bytes, filename: str) -> str:
        """Extract content from Calendar ICS file."""
        try:
            from icalendar import Calendar
            cal = Calendar.from_ical(file_bytes)
            
            events = []
            for component in cal.walk():
                if component.name == "VEVENT":
                    summary = component.get('summary')
                    start = component.get('dtstart')
                    end = component.get('dtend')
                    location = component.get('location')
                    description = component.get('description')
                    
                    event_str = f"Event: {summary}\nStart: {start.dt if start else 'N/A'}\nEnd: {end.dt if end else 'N/A'}"
                    if location: event_str += f"\nLocation: {location}"
                    if description: event_str += f"\nDescription: {description}"
                    events.append(event_str)
            
            result = "[Calendar: " + filename + "]\n\n" + "\n\n---\n\n".join(events)
            logger.info("ics_parsed", filename=filename, events=len(events))
            return result
        except Exception as e:
            # Fallback to plain text decode
            return file_bytes.decode("utf-8", errors="replace")

    def _parse_vcf(self, file_bytes: bytes, filename: str) -> str:
        """Extract content from vCard VCF file."""
        try:
            import vobject
            text = file_bytes.decode("utf-8", errors="replace")
            contacts = []
            for vcard in vobject.readComponents(text):
                name = getattr(vcard, 'fn', getattr(vcard, 'n', 'Unknown'))
                email_val = getattr(vcard, 'email', 'N/A')
                tel = getattr(vcard, 'tel', 'N/A')
                contacts.append(f"Name: {name.value}\nEmail: {email_val.value if hasattr(email_val, 'value') else email_val}\nPhone: {tel.value if hasattr(tel, 'value') else tel}")
            
            result = "[vCard: " + filename + "]\n\n" + "\n\n---\n\n".join(contacts)
            logger.info("vcf_parsed", filename=filename, contacts=len(contacts))
            return result
        except Exception:
            return file_bytes.decode("utf-8", errors="replace")
