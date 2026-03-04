"""
Unified Chart Factory - CANONICAL
==================================

Single source of truth for all chart creation with consistent theming.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional, List, Dict, Any


# Unified Chart Theme
CHART_THEME = {
    'template': 'plotly_dark',
    'color_scheme': {
        'primary': '#00D9FF',      # Cyan
        'secondary': '#FF6B9D',    # Pink
        'success': '#00E676',      # Green
        'warning': '#FFD600',      # Yellow
        'danger': '#FF5252',       # Red
        'neutral': '#B0BEC5',      # Gray
        'background': '#0E1117',   # Dark background
        'surface': '#1E2127',      # Card background
        'text': '#FAFAFA',         # White text
        'text_secondary': '#B0BEC5'  # Gray text
    },
    'fonts': {
        'family': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        'size': 12,
        'title_size': 16,
        'axis_size': 11
    },
    'layout': {
        'height': 500,
        'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60},
        'paper_bgcolor': '#0E1117',
        'plot_bgcolor': '#1E2127',
        'showlegend': True,
        'hovermode': 'x unified'
    }
}


class ChartFactory:
    """
    Factory for creating consistently themed charts.
    
    **CANONICAL CHART FACTORY - DO NOT DUPLICATE**
    """
    
    def __init__(self, theme: Optional[Dict] = None):
        """
        Initialize chart factory with theme.
        
        Args:
            theme: Optional custom theme (defaults to CHART_THEME)
        """
        self.theme = theme or CHART_THEME
    
    def create_line_chart(self, data: Dict[str, List], title: str,
                         x_label: str = "", y_label: str = "",
                         height: Optional[int] = None) -> go.Figure:
        """
        Create a line chart with consistent theming.
        
        Args:
            data: Dictionary with 'x' and one or more y series
            title: Chart title
            x_label: X-axis label
            y_label: Y-axis label
            height: Optional custom height
        
        Returns:
            Plotly Figure
        """
        fig = go.Figure()
        
        colors = [
            self.theme['color_scheme']['primary'],
            self.theme['color_scheme']['secondary'],
            self.theme['color_scheme']['success'],
            self.theme['color_scheme']['warning']
        ]
        
        x_data = data.get('x', [])
        color_idx = 0
        
        for key, values in data.items():
            if key == 'x':
                continue
            
            fig.add_trace(go.Scatter(
                x=x_data,
                y=values,
                name=key,
                mode='lines',
                line=dict(color=colors[color_idx % len(colors)], width=2),
                hovertemplate='%{y:,.2f}<extra></extra>'
            ))
            color_idx += 1
        
        self._apply_layout(fig, title, x_label, y_label, height)
        return fig
    
    def create_bar_chart(self, data: Dict[str, List], title: str,
                        x_label: str = "", y_label: str = "",
                        orientation: str = 'v',
                        height: Optional[int] = None) -> go.Figure:
        """
        Create a bar chart with consistent theming.
        
        Args:
            data: Dictionary with 'x' and 'y' data
            title: Chart title
            x_label: X-axis label
            y_label: Y-axis label
            orientation: 'v' for vertical, 'h' for horizontal
            height: Optional custom height
        
        Returns:
            Plotly Figure
        """
        fig = go.Figure()
        
        # Color bars based on positive/negative values
        colors = [
            self.theme['color_scheme']['success'] if v >= 0 
            else self.theme['color_scheme']['danger']
            for v in data.get('y', [])
        ]
        
        fig.add_trace(go.Bar(
            x=data.get('x', []) if orientation == 'v' else data.get('y', []),
            y=data.get('y', []) if orientation == 'v' else data.get('x', []),
            orientation=orientation,
            marker=dict(color=colors),
            hovertemplate='%{y:,.2f}<extra></extra>' if orientation == 'v' 
                         else '%{x:,.2f}<extra></extra>'
        ))
        
        self._apply_layout(fig, title, x_label, y_label, height)
        return fig
    
    def create_waterfall_chart(self, data: Dict[str, List], title: str,
                              height: Optional[int] = None) -> go.Figure:
        """
        Create a waterfall chart for cashflow analysis.
        
        Args:
            data: Dictionary with 'x' (labels), 'y' (values), 'measure' (types)
            title: Chart title
            height: Optional custom height
        
        Returns:
            Plotly Figure
        """
        fig = go.Figure()
        
        fig.add_trace(go.Waterfall(
            x=data.get('x', []),
            y=data.get('y', []),
            measure=data.get('measure', []),
            increasing=dict(marker=dict(color=self.theme['color_scheme']['success'])),
            decreasing=dict(marker=dict(color=self.theme['color_scheme']['danger'])),
            totals=dict(marker=dict(color=self.theme['color_scheme']['primary'])),
            connector=dict(line=dict(color=self.theme['color_scheme']['neutral'])),
            hovertemplate='%{y:,.0f}<extra></extra>'
        ))
        
        self._apply_layout(fig, title, "", "Amount (ZAR)", height)
        return fig
    
    def create_gauge_chart(self, value: float, title: str,
                          max_value: float = 100,
                          threshold_low: float = 33,
                          threshold_high: float = 66,
                          height: Optional[int] = None) -> go.Figure:
        """
        Create a gauge chart for risk metrics.
        
        Args:
            value: Current value
            title: Chart title
            max_value: Maximum value for gauge
            threshold_low: Low threshold (green/yellow boundary)
            threshold_high: High threshold (yellow/red boundary)
            height: Optional custom height
        
        Returns:
            Plotly Figure
        """
        fig = go.Figure()
        
        fig.add_trace(go.Indicator(
            mode="gauge+number+delta",
            value=value,
            title={'text': title, 'font': {'size': self.theme['fonts']['title_size']}},
            gauge={
                'axis': {'range': [0, max_value]},
                'bar': {'color': self.theme['color_scheme']['primary']},
                'steps': [
                    {'range': [0, threshold_low], 'color': self.theme['color_scheme']['success']},
                    {'range': [threshold_low, threshold_high], 'color': self.theme['color_scheme']['warning']},
                    {'range': [threshold_high, max_value], 'color': self.theme['color_scheme']['danger']}
                ],
                'threshold': {
                    'line': {'color': self.theme['color_scheme']['text'], 'width': 4},
                    'thickness': 0.75,
                    'value': value
                }
            }
        ))
        
        fig.update_layout(
            height=height or 300,
            paper_bgcolor=self.theme['layout']['paper_bgcolor'],
            font={'color': self.theme['color_scheme']['text']}
        )
        
        return fig
    
    def create_heatmap(self, data: Dict[str, Any], title: str,
                      height: Optional[int] = None) -> go.Figure:
        """
        Create a heatmap for correlation or risk matrices.
        
        Args:
            data: Dictionary with 'z' (values), 'x' (columns), 'y' (rows)
            title: Chart title
            height: Optional custom height
        
        Returns:
            Plotly Figure
        """
        fig = go.Figure()
        
        fig.add_trace(go.Heatmap(
            z=data.get('z', []),
            x=data.get('x', []),
            y=data.get('y', []),
            colorscale=[
                [0, self.theme['color_scheme']['danger']],
                [0.5, self.theme['color_scheme']['warning']],
                [1, self.theme['color_scheme']['success']]
            ],
            hovertemplate='%{y} - %{x}: %{z:.2f}<extra></extra>'
        ))
        
        self._apply_layout(fig, title, "", "", height)
        return fig
    
    def _apply_layout(self, fig: go.Figure, title: str,
                     x_label: str, y_label: str,
                     height: Optional[int] = None):
        """Apply consistent layout to figure"""
        layout = self.theme['layout'].copy()
        
        if height:
            layout['height'] = height
        
        fig.update_layout(
            title={
                'text': title,
                'font': {
                    'size': self.theme['fonts']['title_size'],
                    'color': self.theme['color_scheme']['text']
                }
            },
            xaxis_title=x_label,
            yaxis_title=y_label,
            font={
                'family': self.theme['fonts']['family'],
                'size': self.theme['fonts']['size'],
                'color': self.theme['color_scheme']['text']
            },
            **layout
        )


# Convenience function for quick chart creation
def create_chart(chart_type: str, data: Dict, title: str, **kwargs) -> go.Figure:
    """
    Quick chart creation function.
    
    Args:
        chart_type: Type of chart ('line', 'bar', 'waterfall', 'gauge', 'heatmap')
        data: Chart data
        title: Chart title
        **kwargs: Additional arguments for specific chart types
    
    Returns:
        Plotly Figure
    """
    factory = ChartFactory()
    
    chart_methods = {
        'line': factory.create_line_chart,
        'bar': factory.create_bar_chart,
        'waterfall': factory.create_waterfall_chart,
        'gauge': factory.create_gauge_chart,
        'heatmap': factory.create_heatmap
    }
    
    method = chart_methods.get(chart_type)
    if not method:
        raise ValueError(f"Unknown chart type: {chart_type}")
    
    return method(data, title, **kwargs)
