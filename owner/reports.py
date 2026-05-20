from datetime import date, timedelta

from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from accounts.models import User
from core.models import Order

from .views import owner_required

# PDF uchun xavfsiz (lotin) xizmat turi nomlari
SERVICE_LABELS = {
    'light':    'Yengil mashina',
    'heavy':    'Yuk mashina',
    'polish':   'Polirovka',
    'interior': 'Salon tozalash',
    'full':     "To'liq kompleks",
}
OTHER_LABEL = 'Boshqa'


def _first_of_month(d):
    return d.replace(day=1)


def _add_month(d):
    return (d.replace(day=28) + timedelta(days=4)).replace(day=1)


def _gather_stats():
    """Hisobot uchun barcha statistikani yig'adi."""
    completed = Order.objects.filter(status=Order.Status.COMPLETED)

    total_orders  = completed.count()
    total_revenue = int(completed.aggregate(t=Sum('total_price'))['t'] or 0)

    # ── TOP-10 mijozlar (yakunlangan buyurtmalar bo'yicha) ──
    top_rows = (
        completed.values('customer')
        .annotate(orders=Count('id'), revenue=Sum('total_price'))
        .order_by('-revenue')[:10]
    )
    cust_ids = [r['customer'] for r in top_rows]
    users = {u.id: u for u in User.objects.filter(id__in=cust_ids)}
    top_customers = []
    for r in top_rows:
        u = users.get(r['customer'])
        name = (u.get_full_name() or u.email or u.username) if u else f"#{r['customer']}"
        top_customers.append({
            'name':    name,
            'orders':  r['orders'],
            'revenue': int(r['revenue'] or 0),
        })

    # ── Xizmat turi bo'yicha daromad ──
    svc_rows = (
        completed.values('service_ad__service_type')
        .annotate(orders=Count('id'), revenue=Sum('total_price'))
        .order_by('-revenue')
    )
    services = []
    for r in svc_rows:
        code = r['service_ad__service_type']
        services.append({
            'label':   SERVICE_LABELS.get(code, OTHER_LABEL),
            'orders':  r['orders'],
            'revenue': int(r['revenue'] or 0),
        })
    top_service = services[0] if services else None

    # ── Oylik taqqoslash (oxirgi 6 oy) ──
    today = timezone.localdate()
    m = _first_of_month(today)
    back = []
    for _ in range(6):
        back.append(m)
        m = (m - timedelta(days=1)).replace(day=1)
    back.reverse()
    monthly = []
    uz_months = ['Yan', 'Fev', 'Mar', 'Apr', 'May', 'Iyn',
                 'Iyl', 'Avg', 'Sen', 'Okt', 'Noy', 'Dek']
    for ms in back:
        me = _add_month(ms)
        qs = completed.filter(created_at__date__gte=ms, created_at__date__lt=me)
        monthly.append({
            'label':   f"{uz_months[ms.month - 1]} {ms.year}",
            'orders':  qs.count(),
            'revenue': int(qs.aggregate(t=Sum('total_price'))['t'] or 0),
        })

    # ── Haftalik taqqoslash (oxirgi 8 hafta) ──
    weekly = []
    this_week_start = today - timedelta(days=today.weekday())
    for i in range(7, -1, -1):
        ws = this_week_start - timedelta(weeks=i)
        we = ws + timedelta(days=7)
        qs = completed.filter(created_at__date__gte=ws, created_at__date__lt=we)
        weekly.append({
            'label':   ws.strftime('%d.%m'),
            'orders':  qs.count(),
            'revenue': int(qs.aggregate(t=Sum('total_price'))['t'] or 0),
        })

    # ── Joriy oy vs o'tgan oy ──
    cm_start = _first_of_month(today)
    pm_start = (cm_start - timedelta(days=1)).replace(day=1)
    cur_month_rev = int(
        completed.filter(created_at__date__gte=cm_start)
        .aggregate(t=Sum('total_price'))['t'] or 0
    )
    prev_month_rev = int(
        completed.filter(created_at__date__gte=pm_start, created_at__date__lt=cm_start)
        .aggregate(t=Sum('total_price'))['t'] or 0
    )
    if prev_month_rev:
        growth = round((cur_month_rev - prev_month_rev) / prev_month_rev * 100, 1)
    else:
        growth = 100.0 if cur_month_rev else 0.0

    return {
        'total_orders':   total_orders,
        'total_revenue':  total_revenue,
        'top_customers':  top_customers,
        'services':       services,
        'top_service':    top_service,
        'monthly':        monthly,
        'weekly':         weekly,
        'cur_month_rev':  cur_month_rev,
        'prev_month_rev': prev_month_rev,
        'growth':         growth,
    }


@owner_required
def reports(request):
    stats = _gather_stats()
    ctx = dict(stats)
    ctx.update({
        'top_labels':  [c['name'] for c in stats['top_customers']],
        'top_values':  [c['revenue'] for c in stats['top_customers']],
        'svc_labels':  [s['label'] for s in stats['services']],
        'svc_values':  [s['revenue'] for s in stats['services']],
        'm_labels':    [m['label'] for m in stats['monthly']],
        'm_revenue':   [m['revenue'] for m in stats['monthly']],
        'm_orders':    [m['orders'] for m in stats['monthly']],
        'w_labels':    [w['label'] for w in stats['weekly']],
        'w_revenue':   [w['revenue'] for w in stats['weekly']],
        'today':       timezone.localdate().strftime('%d.%m.%Y'),
    })
    return render(request, 'owner/reports.html', ctx)


@owner_required
def report_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    )

    stats = _gather_stats()

    buf = HttpResponse(content_type='application/pdf')
    fname = f"OTTA-hisobot-{timezone.localdate():%Y-%m-%d}.pdf"
    buf['Content-Disposition'] = f'attachment; filename="{fname}"'

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle('h1', parent=styles['Title'], fontSize=20,
                         textColor=colors.HexColor('#0b3a66'))
    h2 = ParagraphStyle('h2', parent=styles['Heading2'], fontSize=13,
                         textColor=colors.HexColor('#0b3a66'), spaceBefore=14)
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=9,
                            textColor=colors.HexColor('#666666'))

    def fmt(n):
        return f"{n:,}".replace(',', ' ')

    story = [
        Paragraph("OTTA Moyka — Statistika hisoboti", h1),
        Paragraph(
            f"Yaratilgan sana: {timezone.localdate():%d.%m.%Y}", small
        ),
        Spacer(1, 10),
    ]

    summary_data = [
        ['Ko\'rsatkich', 'Qiymat'],
        ['Yakunlangan buyurtmalar', fmt(stats['total_orders'])],
        ['Umumiy daromad', fmt(stats['total_revenue']) + " so'm"],
        ['Joriy oy daromadi', fmt(stats['cur_month_rev']) + " so'm"],
        ['O\'tgan oy daromadi', fmt(stats['prev_month_rev']) + " so'm"],
        ['Oylik o\'sish', f"{stats['growth']}%"],
    ]
    if stats['top_service']:
        summary_data.append(
            ['Eng daromadli xizmat',
             f"{stats['top_service']['label']} "
             f"({fmt(stats['top_service']['revenue'])} so'm)"]
        )

    def styled(tbl, head_bg='#0b3a66'):
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(head_bg)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.HexColor('#eef4fb')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        return tbl

    story += [Paragraph("Umumiy ko'rsatkichlar", h2),
              styled(Table(summary_data, colWidths=[80 * mm, 80 * mm]))]

    # TOP-10 mijozlar
    story.append(Paragraph("Eng ko'p daromad keltirgan mijozlar (TOP-10)", h2))
    if stats['top_customers']:
        data = [['#', 'Mijoz', 'Buyurtma', "Daromad (so'm)"]]
        for i, c in enumerate(stats['top_customers'], 1):
            data.append([str(i), c['name'], str(c['orders']), fmt(c['revenue'])])
        story.append(styled(Table(
            data, colWidths=[12 * mm, 78 * mm, 30 * mm, 40 * mm])))
    else:
        story.append(Paragraph("Ma'lumot yo'q.", small))

    # Xizmat turi bo'yicha
    story.append(Paragraph("Xizmat turi bo'yicha daromad", h2))
    if stats['services']:
        data = [['Xizmat turi', 'Buyurtma', "Daromad (so'm)"]]
        for s in stats['services']:
            data.append([s['label'], str(s['orders']), fmt(s['revenue'])])
        story.append(styled(Table(
            data, colWidths=[80 * mm, 40 * mm, 40 * mm])))
    else:
        story.append(Paragraph("Ma'lumot yo'q.", small))

    # Oylik taqqoslash
    story.append(Paragraph("Oylik taqqoslash (oxirgi 6 oy)", h2))
    data = [['Oy', 'Buyurtma', "Daromad (so'm)"]]
    for m in stats['monthly']:
        data.append([m['label'], str(m['orders']), fmt(m['revenue'])])
    story.append(styled(Table(data, colWidths=[80 * mm, 40 * mm, 40 * mm])))

    story += [Spacer(1, 16),
              Paragraph("OTTA Moyka tizimi tomonidan avtomatik yaratildi.", small)]

    doc.build(story)
    return buf
