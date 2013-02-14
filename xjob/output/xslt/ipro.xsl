<?xml version="1.0"?>
<!--
	____ ____ ____ ____    ____ ____ ____ ____ ____ ____ _
	|=== |==< _][_ [___    |==< _][_  ||  |=== _/__ |=== |___

	Stylesheet for LFP (IPro Tech Load File) translation from XML Job file

 	Format for LFP is:
	IM,05100001,D,0,@SFJ_051;001;00000001.TIF;2
	IM,<pageid>,<is attachment starting doc? (C | is starting doc? (D| ))>,<multipage offset>,@<volume>;<relative path>;<filename>;<mimetype code>
-->

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

<xsl:output method="text" />
<xsl:strip-space elements="*" />

<xsl:template match="//page">
<xsl:text />IM,<xsl:value-of select="@id"/><xsl:text />
<xsl:choose><xsl:text />
	<xsl:when test="ancestor::attachment/document/page[position()=1]/@id = @id">,C</xsl:when><xsl:text />
	<xsl:when test="ancestor::document//descendant::page[position()=1]/@id = @id">,D</xsl:when><xsl:text />
	<xsl:otherwise>, </xsl:otherwise><xsl:text />
</xsl:choose>,<xsl:text />
<xsl:choose><xsl:text />
	<xsl:when test="@offset &gt; 0"><xsl:value-of select="@offset" /></xsl:when><xsl:text />
	<xsl:otherwise>0</xsl:otherwise><xsl:text />
</xsl:choose>,@<xsl:text />
<xsl:value-of select="ancestor::box/@id" />;<xsl:text />
<xsl:value-of select="@path" />;<xsl:text />
<xsl:value-of select="@filename" />;<xsl:text />
<xsl:choose><xsl:text />
	<xsl:when test="@mime = 'image/tiff'">2</xsl:when><xsl:text />
	<xsl:when test="@mime = 'application/pdf'">7</xsl:when><xsl:text />
	<xsl:when test="@mime = 'application/jpg'">4</xsl:when><xsl:text />
	<xsl:when test="@mime = 'application/png'">4</xsl:when><xsl:text />
	<xsl:otherwise>2</xsl:otherwise><xsl:text />
</xsl:choose><xsl:text />
<xsl:text disable-output-escaping="yes">
</xsl:text>
</xsl:template>
</xsl:stylesheet>