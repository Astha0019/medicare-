from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date

def format_inr(amount, include_symbol=True):
    """
    Format monetary amounts into Indian numbering system with optional ₹ symbol.
    Example: 125000.50 -> ₹1,25,000.50
             10000000 -> ₹1,00,00,000.00
    """
    if amount is None:
        amount = Decimal('0.00')
    if not isinstance(amount, Decimal):
        try:
            amount = Decimal(str(amount))
        except Exception:
            amount = Decimal('0.00')

    is_negative = amount < 0
    amount = abs(amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    parts = f"{amount:.2f}".split('.')
    integer_part = parts[0]
    decimal_part = parts[1]

    # Indian numbering formatting:
    # Rightmost 3 digits, then groups of 2 digits
    if len(integer_part) > 3:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        formatted_int = ','.join(groups) + ',' + last_three
    else:
        formatted_int = integer_part

    result = f"{formatted_int}.{decimal_part}"
    if is_negative:
        return f"-₹{result}" if include_symbol else f"-{result}"
    return f"₹{result}" if include_symbol else result


def format_date(dt):
    """Format date to DD-MM-YYYY"""
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.strptime(dt, '%Y-%m-%d').date()
        except Exception:
            return dt
    return dt.strftime('%d-%m-%Y')


def format_datetime(dt):
    """Format datetime to DD-MM-YYYY hh:mm AM/PM"""
    if not dt:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime('%d-%m-%Y %I:%M %p')


def number_to_words_inr(amount):
    """
    Converts amount to Indian currency words format.
    e.g., 1450.50 -> "Rupees One Thousand Four Hundred Fifty and Fifty Paise Only"
    """
    if amount is None:
        amount = Decimal('0.00')
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    amount = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    rupees = int(amount)
    paise = int((amount - rupees) * 100)

    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
            "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
            "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def convert_two_digits(n):
        if n < 20:
            return ones[n]
        return tens[n // 10] + (" " + ones[n % 10] if (n % 10 != 0) else "")

    def convert_three_digits(n):
        if n >= 100:
            rem = n % 100
            res = ones[n // 100] + " Hundred"
            if rem > 0:
                res += " and " + convert_two_digits(rem)
            return res
        return convert_two_digits(n)

    if rupees == 0:
        words = "Zero"
    else:
        parts = []
        crores = rupees // 10000000
        rupees %= 10000000
        if crores > 0:
            parts.append(convert_two_digits(crores) + " Crore")

        lakhs = rupees // 100000
        rupees %= 100000
        if lakhs > 0:
            parts.append(convert_two_digits(lakhs) + " Lakh")

        thousands = rupees // 1000
        rupees %= 1000
        if thousands > 0:
            parts.append(convert_two_digits(thousands) + " Thousand")

        hundreds = rupees
        if hundreds > 0:
            parts.append(convert_three_digits(hundreds))

        words = " ".join(parts).strip()

    result = f"Rupees {words}"
    if paise > 0:
        result += f" and {convert_two_digits(paise)} Paise"
    result += " Only"
    return result
