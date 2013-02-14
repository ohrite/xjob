<?xml version="1.0"?>
<!--
	____ ____ ____ ____    ____ ____ ____ ____ ____ ____ _
	|=== |==< _][_ [___    |==< _][_  ||  |=== _/__ |=== |___

	Transform for Opticon (Concordance Load File) from XML Job file

 	Format for Opticon load file is:
	SFJ0097694,SFJ017,D:\SFJ\0097694\SFJ0097694.tif,Y,,,
	<pageid>,<volume>,<absolute path>,<is starting doc? (Y|)>,,,<number of pages (not used)>
-->

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

<xsl:output method="text" />
<xsl:strip-space elements="*" />

<xsl:template match="//page">
<xsl:text /><xsl:value-of select="@id" />,<xsl:text />
<xsl:value-of select="ancestor::volume/@id" />,<xsl:text />
<xsl:value-of select="ancestor::job/@path" /><xsl:text />
<xsl:value-of select="@path" />\<xsl:text />
<xsl:value-of select="@filename" />,<xsl:text />
<xsl:if test="ancestor::document//descendant::page[position()=1]/@id = @id">Y</xsl:if>,,,<xsl:text />
<xsl:text disable-output-escaping="yes">
</xsl:text>
</xsl:template>
</xsl:stylesheet>