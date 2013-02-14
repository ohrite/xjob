<?xml version="1.0"?>
<!--
	____ ____ ____ ____    ____ ____ ____ ____ ____ ____ _
	|=== |==< _][_ [___    |==< _][_  ||  |=== _/__ |=== |___

	Stylesheet for Summation (Image) translation from XML Job file

 	Format for LFP is:
	@T SFJ0097696
	@D @I:\SFJ\0097694\ 
	SFJ0097696.tif
	...

	@T <document id>
	@D @I:<relative path>
	<page file>
	...
-->

<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

<xsl:output method="text" />
<xsl:strip-space elements="*" />

<xsl:template match="document">
<xsl:for-each select="/descendant-or-self::document"><xsl:text />
<xsl:text />@T <xsl:value-of select="child::page[position()=1]/@id" /><xsl:text />
@D @I<xsl:value-of select="child::page[position()=1]/@path" />\<xsl:text />
<xsl:text disable-output-escaping="yes">
</xsl:text><xsl:text />
<xsl:for-each select="child::page">
<xsl:value-of select="@filename" /><xsl:text disable-output-escaping="yes">
</xsl:text>
</xsl:for-each>
<xsl:text disable-output-escaping="yes">
</xsl:text>
</xsl:for-each>
</xsl:template>
</xsl:stylesheet>