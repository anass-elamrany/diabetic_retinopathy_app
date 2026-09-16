from django.utils import timezone
from .models import RetinaImage

def get_stage_distribution(user):
    """Calculate distribution of DR stages for a user"""
    try:
        stage_distribution = [0, 0, 0, 0, 0]  # For stages 0-4
        images = RetinaImage.objects.filter(analyzed_by=user, confidence__gt=0)
        
        for image in images:
            if image.stage is not None and 0 <= image.stage <= 4:
                stage_distribution[image.stage] += 1
        
        return {
            'data': stage_distribution,
            'success': True
        }
    except Exception as e:
        return {
            'error': f"Error calculating stage distribution: {str(e)}",
            'success': False
        }

def get_monthly_trend(user):
    """Calculate monthly analysis trend for last 6 months"""
    try:
        monthly_data = []
        monthly_labels = []
        
        today = timezone.localdate()
        for i in range(5, -1, -1):
            month_index = today.year * 12 + today.month - 1 - i
            year, zero_based_month = divmod(month_index, 12)
            month_number = zero_based_month + 1
            month = today.replace(year=year, month=month_number, day=1)
            count = RetinaImage.objects.filter(
                analyzed_by=user,
                confidence__gt=0,
                uploaded_at__month=month_number,
                uploaded_at__year=year
            ).count()
            monthly_data.append(count)
            monthly_labels.append(month.strftime("%b %Y"))
        
        return {
            'labels': monthly_labels,
            'data': monthly_data,
            'success': True
        }
    except Exception as e:
        return {
            'error': f"Error calculating monthly trend: {str(e)}",
            'success': False
        }

def get_chart_data(user):
    """Get all chart data for dashboard"""
    return {
        'stage_data': get_stage_distribution(user),
        'monthly_data': get_monthly_trend(user)
    }
