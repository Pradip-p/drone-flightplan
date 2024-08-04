#!/usr/bin/python3
"""
Sample a Digital Elevation Model raster values at points. Primarily intended
as a library; the associated flightPlanWaypointGenerator uses it to add an
elevation column to a grid of autogenerated waypoints.

However, it can be used standalone to sample a given DEM (GeoTIFF) at the
points given by a given GeoJSON point layer.
"""

import argparse

from osgeo import ogr, gdal, osr
import math
import struct
import csv


def sampleRasterFromPointsList(raster_file, points_list):
    """
    Arguments:
    DEM raster file as geotiff
    A list of points. Each point consists of [index, x, y] in EPSG:3857
    """

    r = gdal.Open(raster_file)
    rasterSR = osr.SpatialReference()
    rasterSR.ImportFromProj4(r.GetProjection())
    print("\nRaster Coordinate Reference System:")
    print(rasterSR)
    band = r.GetRasterBand(1)
    print("\nRaster band 1 data type:")
    rasterDataType = gdal.GetDataTypeName(band.DataType)
    print(rasterDataType)
    forward = r.GetGeoTransform()
    reverse = gdal.InvGeoTransform(forward)
    print(f"\nRaster forward geotransform: {forward}")
    print(f"\nRaster reverse geotransform: {reverse}")

    pointSR = osr.SpatialReference()
    pointSR.ImportFromEPSG(3857)
    # print(pointSR.GetName)

    transform = osr.CoordinateTransformation(pointSR, rasterSR)
    # print(f'\nPoint layer transform: {transform}')

    points = []

    for feature in points_list:
        pointXYRasterCRS = transform.TransformPoint(feature[1], feature[2])
        mapX = pointXYRasterCRS[1]
        mapY = pointXYRasterCRS[0]
        pixcoords = gdal.ApplyGeoTransform(reverse, mapX, mapY)
        pixX = math.floor(pixcoords[0])
        pixY = math.floor(pixcoords[1])
        elevationstruct = band.ReadRaster(pixX, pixY, 1, 1)
        # TODO The struct needs to be unpacked based on the data type in the DEM.
        # Currently we're unpacking a littlendian int16 ('<h'), which
        # corresponds to what we're getting from the global JAXA DEM, but that
        # won't be consistent across DEMs.
        elevation = struct.unpack("<h", elevationstruct)[0]
        # print(f'Point coordinates in point layer CRS: {geom}')
        # print(f'Point coordinates in raster layer CRS: {mapX}, {mapY}')
        # print(f'Pixel coordinates: {pixX}, {pixY}')
        # print(f'Elevation at point: {elevation}')
        points.append([feature[0], feature[1], feature[2], elevation])
    return points


def rasterValuesAtPoints(raster_file, point_file):
    """
    Arguments:
    DEM raster file as geotiff
    Point file as GeoJSON
    """

    r = gdal.Open(raster_file)
    rasterSR = osr.SpatialReference()
    # rasterSR.ImportFromEPSG(4326) #ONLY FOR TESTING
    rasterSR.ImportFromProj4(r.GetProjection())
    print("\nRaster Coordinate Reference System:")
    print(rasterSR)
    band = r.GetRasterBand(1)
    print("\nRaster band 1 data type:")
    rasterDataType = gdal.GetDataTypeName(band.DataType)
    print(rasterDataType)
    forward = r.GetGeoTransform()
    reverse = gdal.InvGeoTransform(forward)
    print(f"\nRaster forward geotransform: {forward}")
    print(f"\nRaster reverse geotransform: {reverse}")

    p = ogr.Open(point_file)
    lyr = p.GetLayer()
    print("\nPoint layer Coordinate Reference System:")
    pointSR = lyr.GetSpatialRef()
    print(pointSR.GetName)

    transform = osr.CoordinateTransformation(pointSR, rasterSR)
    print(f"\nPoint layer transform: {transform}")
    points = []
    for feature in lyr:
        geom = feature.GetGeometryRef()
        pointXYRasterCRS = transform.TransformPoint(geom.GetX(), geom.GetY())
        mapX = pointXYRasterCRS[1]
        mapY = pointXYRasterCRS[0]
        pixcoords = gdal.ApplyGeoTransform(reverse, mapX, mapY)
        pixX = math.floor(pixcoords[0])
        pixY = math.floor(pixcoords[1])
        elevationstruct = band.ReadRaster(pixX, pixY, 1, 1)
        elevation = struct.unpack("f", elevationstruct)[0]
        # print(f'Point coordinates in point layer CRS: {geom}')
        # print(f'Point coordinates in raster layer CRS: {mapX}, {mapY}')
        # print(f'Pixel coordinates: {pixX}, {pixY}')
        # print(f'Elevation at point: {elevation}')

        # TODO: check what CRS this returns, probably x and y should
        # be returned in the same CRS as the input file

        # TODO: this won't include an index, and will discard any fields
        # that came with the original GeoJSON.
        points.append([mapX, mapY, elevation])
    return points


def gridWithElevation2csv(grid, outfile):
    """Writes a CSV file from a grid with an elevation column"""
    with open(outfile, "w") as of:
        w = csv.writer(of)
        w.writerow(["x", "y", "elevation"])
        w.writerows(grid)


if __name__ == "__main__":
    p = argparse.ArgumentParser()

    p.add_argument("inraster", help="input DEM GeoTIFF raster file")
    p.add_argument("inpoints", help="input points geojson file")
    p.add_argument("outfile", help="output csv file")

    a = p.parse_args()

    grid = rasterValuesAtPoints(a.inraster, a.inpoints)
    gridfile = gridWithElevation2csv(grid, a.outfile)
