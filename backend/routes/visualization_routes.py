"""
Advanced Visualization Routes

Provides intelligent graph generation based on data analysis and user requests.
Supports multiple chart types: histograms, scatter plots, line charts, heatmaps, 3D plots, etc.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import numpy as np

from database import get_db
from models import ArgoProfile
from dependencies import get_current_user

router = APIRouter(prefix="/visualization", tags=["visualization"])


@router.get("/chart-data")
async def get_chart_data(
    chart_type: str = Query(..., description="Type of chart: histogram, scatter, line, heatmap, 3d_scatter, depth_profile, correlation"),
    variable: Optional[str] = Query(None, description="Primary variable: temperature, salinity, depth, pressure"),
    variable_y: Optional[str] = Query(None, description="Secondary variable for scatter plots"),
    limit: int = Query(200, le=1000),
    source: str = Query("local", description="Data source: live (ERDDAP) or local (SQLite)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Generate intelligent chart data based on type and variables.
    Defaults to live ERDDAP data with SQLite fallback.
    """

    # Try live ERDDAP first
    if source == "live":
        try:
            from erddap_service import get_erddap_service
            svc = get_erddap_service()

            if chart_type == "histogram" and variable:
                return svc.chart_data_histogram(variable, limit)
            elif chart_type == "scatter" and variable and variable_y:
                return svc.chart_data_scatter(variable, variable_y, limit)
            elif chart_type == "depth_profile" and variable:
                return svc.chart_data_depth_profile(variable, limit)
            elif chart_type == "heatmap" and variable:
                return svc.chart_data_heatmap(variable, limit)
            elif chart_type == "3d_scatter":
                return svc.chart_data_3d_scatter(limit)
            elif chart_type == "correlation":
                return svc.chart_data_correlation(limit)
            elif chart_type == "line" and variable:
                return svc.chart_data_line(variable, limit)
        except Exception:
            pass  # fall through to SQLite

    # SQLite fallback
    
    try:
        if chart_type == "histogram":
            return await generate_histogram(db, variable, limit)
        
        elif chart_type == "scatter":
            return await generate_scatter(db, variable, variable_y, limit)
        
        elif chart_type == "depth_profile":
            return await generate_depth_profile(db, variable, limit)
        
        elif chart_type == "heatmap":
            return await generate_heatmap(db, variable, limit)
        
        elif chart_type == "3d_scatter":
            return await generate_3d_scatter(db, limit)
        
        elif chart_type == "correlation":
            return await generate_correlation_matrix(db, limit)
        
        elif chart_type == "line":
            return await generate_line_chart(db, variable, limit)
        
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported chart type: {chart_type}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chart generation failed: {str(e)}")


async def generate_histogram(db: Session, variable: str, limit: int):
    """Generate histogram data for a single variable."""
    
    # Map variable names
    var_map = {
        'temperature': ArgoProfile.temperature,
        'salinity': ArgoProfile.salinity,
        'depth': ArgoProfile.depth,
        'pressure': ArgoProfile.pressure
    }
    
    if variable not in var_map:
        raise HTTPException(status_code=400, detail=f"Invalid variable: {variable}")
    
    column = var_map[variable]
    
    # Query data
    profiles = db.query(column).filter(column.isnot(None)).limit(limit).all()
    values = [p[0] for p in profiles if p[0] is not None]
    
    if not values:
        return {"error": "No data available", "values": []}
    
    return {
        "chart_type": "histogram",
        "variable": variable,
        "values": values,
        "stats": {
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "count": len(values)
        },
        "metadata": {
            "title": f"{variable.capitalize()} Distribution",
            "xlabel": f"{variable.capitalize()} ({'°C' if variable == 'temperature' else 'PSU' if variable == 'salinity' else 'm'})",
            "ylabel": "Frequency"
        }
    }


async def generate_scatter(db: Session, variable_x: str, variable_y: str, limit: int):
    """Generate scatter plot data for two variables."""
    
    var_map = {
        'temperature': ArgoProfile.temperature,
        'salinity': ArgoProfile.salinity,
        'depth': ArgoProfile.depth,
        'pressure': ArgoProfile.pressure,
        'latitude': ArgoProfile.latitude,
        'longitude': ArgoProfile.longitude
    }
    
    if variable_x not in var_map or variable_y not in var_map:
        raise HTTPException(status_code=400, detail="Invalid variable")
    
    col_x = var_map[variable_x]
    col_y = var_map[variable_y]
    
    # Query data
    profiles = db.query(col_x, col_y).filter(
        col_x.isnot(None), col_y.isnot(None)
    ).limit(limit).all()
    
    if not profiles:
        return {"error": "No data available"}
    
    x_values = [p[0] for p in profiles]
    y_values = [p[1] for p in profiles]
    
    # Calculate correlation
    correlation = np.corrcoef(x_values, y_values)[0, 1]
    
    return {
        "chart_type": "scatter",
        "x_variable": variable_x,
        "y_variable": variable_y,
        "x_values": x_values,
        "y_values": y_values,
        "correlation": float(correlation),
        "metadata": {
            "title": f"{variable_y.capitalize()} vs {variable_x.capitalize()}",
            "xlabel": variable_x.capitalize(),
            "ylabel": variable_y.capitalize()
        }
    }


async def generate_depth_profile(db: Session, variable: str, limit: int):
    """Generate depth profile (depth vs measurement)."""
    
    var_map = {
        'temperature': ArgoProfile.temperature,
        'salinity': ArgoProfile.salinity,
        'pressure': ArgoProfile.pressure
    }
    
    if variable not in var_map:
        raise HTTPException(status_code=400, detail=f"Invalid variable: {variable}")
    
    column = var_map[variable]
    
    # Query depth and variable
    profiles = db.query(ArgoProfile.depth, column).filter(
        ArgoProfile.depth.isnot(None),
        column.isnot(None)
    ).order_by(ArgoProfile.depth).limit(limit).all()
    
    if not profiles:
        return {"error": "No data available"}
    
    depths = [p[0] for p in profiles]
    values = [p[1] for p in profiles]
    
    return {
        "chart_type": "depth_profile",
        "variable": variable,
        "depths": depths,
        "values": values,
        "metadata": {
            "title": f"Depth Profile: {variable.capitalize()}",
            "xlabel": f"{variable.capitalize()} ({'°C' if variable == 'temperature' else 'PSU' if variable == 'salinity' else 'dbar'})",
            "ylabel": "Depth (m)"
        }
    }


async def generate_heatmap(db: Session, variable: str, limit: int):
    """Generate heatmap data (spatial distribution)."""
    
    var_map = {
        'temperature': ArgoProfile.temperature,
        'salinity': ArgoProfile.salinity,
        'depth': ArgoProfile.depth
    }
    
    if variable not in var_map:
        raise HTTPException(status_code=400, detail=f"Invalid variable: {variable}")
    
    column = var_map[variable]
    
    # Query location and variable
    profiles = db.query(
        ArgoProfile.latitude,
        ArgoProfile.longitude,
        column
    ).filter(column.isnot(None)).limit(limit).all()
    
    if not profiles:
        return {"error": "No data available"}
    
    lats = [p[0] for p in profiles]
    lons = [p[1] for p in profiles]
    values = [p[2] for p in profiles]
    
    return {
        "chart_type": "heatmap",
        "variable": variable,
        "latitudes": lats,
        "longitudes": lons,
        "values": values,
        "metadata": {
            "title": f"Spatial Distribution: {variable.capitalize()}",
            "xlabel": "Longitude",
            "ylabel": "Latitude"
        }
    }


async def generate_3d_scatter(db: Session, limit: int):
    """Generate 3D scatter plot (temperature, salinity, depth)."""
    
    profiles = db.query(
        ArgoProfile.temperature,
        ArgoProfile.salinity,
        ArgoProfile.depth
    ).filter(
        ArgoProfile.temperature.isnot(None),
        ArgoProfile.salinity.isnot(None),
        ArgoProfile.depth.isnot(None)
    ).limit(limit).all()
    
    if not profiles:
        return {"error": "No data available"}
    
    temps = [p[0] for p in profiles]
    sals = [p[1] for p in profiles]
    depths = [p[2] for p in profiles]
    
    return {
        "chart_type": "3d_scatter",
        "temperature": temps,
        "salinity": sals,
        "depth": depths,
        "metadata": {
            "title": "3D Ocean Properties",
            "xlabel": "Temperature (°C)",
            "ylabel": "Salinity (PSU)",
            "zlabel": "Depth (m)"
        }
    }


async def generate_correlation_matrix(db: Session, limit: int):
    """Generate correlation matrix for all numeric variables."""
    
    profiles = db.query(
        ArgoProfile.temperature,
        ArgoProfile.salinity,
        ArgoProfile.depth,
        ArgoProfile.pressure
    ).filter(
        ArgoProfile.temperature.isnot(None),
        ArgoProfile.salinity.isnot(None),
        ArgoProfile.depth.isnot(None)
    ).limit(limit).all()
    
    if not profiles:
        return {"error": "No data available"}
    
    # Convert to numpy array
    data = np.array([[p[0], p[1], p[2], p[3] or 0] for p in profiles])
    
    # Calculate correlation matrix
    corr_matrix = np.corrcoef(data.T)
    
    variables = ['Temperature', 'Salinity', 'Depth', 'Pressure']
    
    return {
        "chart_type": "correlation",
        "variables": variables,
        "correlation_matrix": corr_matrix.tolist(),
        "metadata": {
            "title": "Variable Correlation Matrix"
        }
    }


async def generate_line_chart(db: Session, variable: str, limit: int):
    """Generate line chart (sequential measurements)."""
    
    var_map = {
        'temperature': ArgoProfile.temperature,
        'salinity': ArgoProfile.salinity,
        'depth': ArgoProfile.depth
    }
    
    if variable not in var_map:
        raise HTTPException(status_code=400, detail=f"Invalid variable: {variable}")
    
    column = var_map[variable]
    
    # Query data ordered by ID (sequential)
    profiles = db.query(ArgoProfile.id, column).filter(
        column.isnot(None)
    ).order_by(ArgoProfile.id).limit(limit).all()
    
    if not profiles:
        return {"error": "No data available"}
    
    indices = [p[0] for p in profiles]
    values = [p[1] for p in profiles]
    
    return {
        "chart_type": "line",
        "variable": variable,
        "indices": indices,
        "values": values,
        "metadata": {
            "title": f"{variable.capitalize()} Sequence",
            "xlabel": "Profile ID",
            "ylabel": f"{variable.capitalize()}"
        }
    }
