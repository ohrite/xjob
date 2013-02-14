<?xml version="1.0"?>
<!--
	____ ____ ____ ____    ____ ____ ____ ____ ____ ____ _
	|=== |==< _][_ [___    |==< _][_  ||  |=== _/__ |=== |___

	Transform sheet for Document-level CSV report from XML Job file
	Notice that <xsl:text /> is used all over the place for output escaping.  don't ask.

 	Format for doclevel CSV file is:
	"Column Name",...
	"Value",...
-->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

<xsl:output method="text" />
<xsl:strip-space elements="*" />

<xsl:template match="/">
<xsl:text disable-output-escaping="yes">"BEGNUM","ENDNUM","PAGES","BOXNAME","CDVOL","FOLDERSTART","FOLDEREND","FOLDERTITLE","ATTACHSTART","ATTACHEND","BOXSOURCE"
</xsl:text>
<xsl:apply-templates />
</xsl:template>

<xsl:template match="document"><xsl:text />
<xsl:for-each select="/descendant-or-self::document"><xsl:text />
<xsl:text />"<xsl:value-of select="page[position()=1]/@id" />",<xsl:text />
<xsl:text />"<xsl:value-of select="page[last()]/@id" />",<xsl:text />
<xsl:text />"<xsl:value-of select="count(page)" />",<xsl:text />
<xsl:text />"<xsl:value-of select="ancestor::box/@boxsrc" />",<xsl:text />
<xsl:text />"<xsl:value-of select="ancestor::box/@id" />",<xsl:text />
<xsl:text />"<xsl:value-of select="ancestor::folder/descendant::page[position()=1]/@id" />",<xsl:text />
<xsl:text />"<xsl:value-of select="ancestor::folder/descendant::page[last()]/@id" />",<xsl:text />
<xsl:text />"<xsl:choose><xsl:text />
<xsl:text /><xsl:when test="ancestor::folder"><xsl:value-of select="ancestor::folder/@name" /></xsl:when><xsl:text />
<xsl:text /><xsl:otherwise><xsl:value-of select="@container" /></xsl:otherwise><xsl:text />
<xsl:text /></xsl:choose>",<xsl:text />
<xsl:text />"<xsl:value-of select="ancestor::attachment/descendant::page[position()=1]/@id" />",<xsl:text />
<xsl:text />"<xsl:value-of select="ancestor::attachment/descendant::page[last()]/@id" />",<xsl:text />
<xsl:text />"<xsl:value-of select="ancestor::box/@src" />"<xsl:text />
<xsl:text disable-output-escaping="yes">
</xsl:text>
</xsl:for-each>
</xsl:template>
</xsl:stylesheet>