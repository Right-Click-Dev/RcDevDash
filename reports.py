from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus import Image as RLImage
from datetime import datetime, timedelta
import os
import tempfile


def generate_project_report(project):
    """
    Generate a professional PDF report for a project

    Args:
        project: Project model instance

    Returns:
        str: Path to the generated PDF file
    """
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf_path = temp_file.name
    temp_file.close()

    # Create the PDF document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch
    )

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0d6efd'),
        spaceAfter=30,
        alignment=1  # Center
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#0d6efd'),
        spaceAfter=12,
        spaceBefore=12
    )
    normal_style = styles['Normal']

    # Title
    title = Paragraph(f"Project Report: {project.name}", title_style)
    elements.append(title)

    # Report date
    report_date = Paragraph(
        f"<b>Report Generated:</b> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
        normal_style
    )
    elements.append(report_date)
    elements.append(Spacer(1, 0.3*inch))

    # Project Information Section
    elements.append(Paragraph("Project Information", heading_style))

    project_info = [
        ['Project Name:', project.name],
        ['Description:', project.description or 'No description provided'],
        ['Created:', project.created_at.strftime('%B %d, %Y')],
        ['Last Updated:', project.updated_at.strftime('%B %d, %Y')],
    ]

    project_table = Table(project_info, colWidths=[2*inch, 4.5*inch])
    project_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#495057')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elements.append(project_table)
    elements.append(Spacer(1, 0.3*inch))

    # Hours Summary Section
    elements.append(Paragraph("Hours Summary", heading_style))

    # Calculate percentages and status
    budget_status = "Over Budget" if project.is_over_budget else "Within Budget"
    status_color = colors.red if project.is_over_budget else colors.green

    hours_data = [
        ['Metric', 'Hours', 'Percentage'],
        ['Hours Budget', f"{project.hours_budget:.1f}", '100%'],
        ['Hours Used', f"{project.hours_used:.1f}", f"{project.progress_percentage:.1f}%"],
        ['Hours Remaining', f"{project.hours_remaining:.1f}",
         f"{(project.hours_remaining/project.hours_budget*100 if project.hours_budget > 0 else 0):.1f}%"],
        ['Status', budget_status, ''],
    ]

    hours_table = Table(hours_data, colWidths=[2*inch, 2*inch, 2.5*inch])
    hours_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0d6efd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('TEXTCOLOR', (1, -1), (1, -1), status_color),
        ('FONTNAME', (1, -1), (1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
    ]))
    elements.append(hours_table)
    elements.append(Spacer(1, 0.3*inch))

    # Work Items Section
    elements.append(Paragraph("Work Items History", heading_style))

    if project.work_items:
        # Calculate weekly summary
        one_week_ago = datetime.now() - timedelta(days=7)
        recent_items = [item for item in project.work_items if item.work_date >= one_week_ago]

        if recent_items:
            elements.append(Paragraph(
                f"<b>Recent Activity (Last 7 Days):</b> {len(recent_items)} work items, "
                f"{sum(item.hours for item in recent_items):.1f} hours",
                normal_style
            ))
            elements.append(Spacer(1, 0.1*inch))

        work_items_data = [['Date', 'Description', 'Hours']]
        for item in sorted(project.work_items, key=lambda x: x.work_date, reverse=True):
            work_items_data.append([
                item.work_date.strftime('%m/%d/%Y'),
                item.description[:60] + ('...' if len(item.description) > 60 else ''),
                f"{item.hours:.2f}"
            ])

        work_items_table = Table(work_items_data, colWidths=[1.2*inch, 4*inch, 1.3*inch])
        work_items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#198754')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(work_items_table)
    else:
        elements.append(Paragraph("<i>No work items recorded yet.</i>", normal_style))

    elements.append(Spacer(1, 0.3*inch))

    # Tasks Section
    elements.append(Paragraph("Task List", heading_style))

    if project.tasks:
        completed_tasks = [t for t in project.tasks if t.completed]
        pending_tasks = [t for t in project.tasks if not t.completed]

        elements.append(Paragraph(
            f"<b>Task Summary:</b> {len(completed_tasks)} completed, {len(pending_tasks)} pending",
            normal_style
        ))
        elements.append(Spacer(1, 0.1*inch))

        tasks_data = [['Status', 'Description', 'Deadline']]
        for task in sorted(project.tasks, key=lambda x: (x.completed, x.deadline or datetime.max.date())):
            status = '✓ Complete' if task.completed else '○ Pending'
            deadline = task.deadline.strftime('%m/%d/%Y') if task.deadline else 'No deadline'

            # Check if overdue
            if task.is_overdue:
                deadline += ' (OVERDUE)'

            tasks_data.append([
                status,
                task.description[:50] + ('...' if len(task.description) > 50 else ''),
                deadline
            ])

        tasks_table = Table(tasks_data, colWidths=[1.3*inch, 3.7*inch, 1.5*inch])
        tasks_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0dcaf0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(tasks_table)
    else:
        elements.append(Paragraph("<i>No tasks created yet.</i>", normal_style))

    # Footer
    elements.append(Spacer(1, 0.5*inch))
    footer_text = Paragraph(
        "<i>This report was generated automatically by RcDevDash Project Planning Dashboard.</i>",
        ParagraphStyle('Footer', parent=normal_style, fontSize=8, textColor=colors.grey, alignment=1)
    )
    elements.append(footer_text)

    # Build PDF
    doc.build(elements)

    return pdf_path
