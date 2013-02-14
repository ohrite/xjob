# DarkHorse query library
# Eric Ritezel -- February 14, 2007
#

# all the fields that can possibly be exported from the database
ExportFields = ("Bates Start", "Bates End", "Attach Start",
	"Attach End", "TotalNumberOfPages", "FileHash", "Media Name",
	"!FS_DateLastModified", "!FS_Filename", "!FS_Path", "!FS_Size",
	"!FS_Extension", "Email_MessageId", "Format", "PST_Report",
	"Email_Outlook Header", "Date Created", "Document Date", "Author",
	"Subject", "Recipient", "Email_Importance", "Email_Received Date",
	"Email_Sub Type", "Email_SysId", "Email_Topic", "Email_Topic Index",
	"Email_Attachment Count", "CC", "Email_Attachment Name",
	"Email_Attachment List", "PST_Qc", "Company", "Security",
	"Date Last Printed", "Spreadsheet_Sheets", "Spreadsheet_Charts",
	"Spreadsheet_Chart Objects", "Spreadsheet_Sheet Names",
	"Spreadsheet_Overlap Text", "Spreadsheet_Object Names",
	"Spreadsheet_Object Title", "Title", "Number of Revisions",
	"Event Period", "Has Macro", "Revision Count", "Revisions",
	"Pages of Document", "BCC", "Edit Time", "Power Point_User Notes",
	"Comments", "Spreadsheet_Chart Names", "Spreadsheet_Chart Title",
	"Category", "TextFilePath")

# the root paths for the files and images on the NAS
GetRoots = """\
SELECT ImageRoot, FileRoot FROM FirmCases WITH (NOLOCK)
WHERE FirmID=%(firm)05d AND CaseID=%(case)05d"""

# Fetch all the documents (and some useful information) from the view
GetAllViewDocs = """\
SET NOCOUNT ON;
SELECT vd.DocumentID, docs.FileID, tf.TranslatedFileID,
       mod.DocumentID as Modified, COUNT(nump.NumPages) as NumPages
    FROM ViewDocuments_%(view)d AS vd WITH (NOLOCK)
LEFT JOIN Documents AS docs WITH (NOLOCK)
    ON docs.DocumentID = vd.DocumentID
LEFT JOIN TranslatedFiles AS tf WITH (NOLOCK)
    ON tf.OriginalFileID = docs.FileID
LEFT JOIN (
    SELECT DISTINCT DocumentID FROM DocumentPages AS dp1 WITH (NOLOCK)
    JOIN PageImageFiles AS pif WITH (NOLOCK) ON dp1.PageID = pif.PageID
    WHERE pif.ImageType = 2) AS mod
    ON mod.DocumentID = vd.DocumentID
LEFT JOIN (
    SELECT DocumentID, DocumentPages_ID AS NumPages
        FROM DocumentPages WITH (NOLOCK)) AS nump
    ON nump.DocumentID = vd.DocumentID
WHERE vd.ViewID = %(view)d
GROUP BY vd.DocNumOrder, vd.DocumentID, docs.FileID,
         tf.TranslatedFileID, mod.DocumentID"""

# Fetch all the attachments (and some useful information) from the view
GetAllAttachments = """\
SELECT at.AttachmentID, at.DocumentID, at.DocAttachmentOrder
    FROM ViewDocuments_%(view)d AS vd WITH (NOLOCK)
RIGHT JOIN Attachments AS at WITH (NOLOCK)
    ON at.DocumentID = vd.DocumentID
WHERE vd.ViewID = %(view)d
ORDER BY at.AttachmentID, at.DocAttachmentOrder"""

# Fetch all Bates numbers from the view
GetAllBates = """\
"""

# Fetch all Document numbers from the view
GetAllID = """\
"""

# Fetch all the metadata from the view
GetAllFieldData = """\
"""

GetImagePath = """\
SELECT imf.ImageFilePath, pif.ImageType FROM DocumentPages AS dp WITH (NOLOCK)
	ON dp.PageID = pif.PageID
INNER JOIN ImageFiles AS imf WITH (NOLOCK)
	ON pif.ImageFileID = imf.ImageFileID
WHERE dp.DocumentID = %(did)s AND pif.IsRemoved = 0 AND ImageType IN
	(SELECT MAX(ImageType) AS ImageType FROM PageImageFiles WITH (NOLOCK)
		WHERE PageID = dp.PageID)
ORDER BY dp.DocumentPageOrder, pif.ImageType DESC"""

GetNativeFileInfo = """\
SELECT DHFileTypeCode, f.StorageSize FROM Files AS f WITH(NOLOCK)
JOIN %(prefix)sGlobalData..DHFileTypes AS dt
	ON f.DHFileTypeID = dt.DHFileTypeID
WHERE f.FileID = %(fileid)d"""

GetNativeFileData = """\
SELECT fd.Data FROM Fields AS f WITH (NOLOCK)
JOIN CaseConstraints AS cc WITH (NOLOCK)
	ON f.FieldName = cc.StringValue AND cc.Constname = 'ED_FIELD_FILENAME'
JOIN FieldData AS fd WITH (NOLOCK)
	ON f.FieldID = fd.FieldID AND fd.DocumentID = %(did)s"""

GetDocNumber = """\
SELECT * FROM DocumentNumber AS dn WITH (NOLOCK)
JOIN BatesTypes AS bt WITH (NOLOCK)
	ON dn.BatesType = bt.BatesType
WHERE dn.DocumentID = %(did)s AND bt.BatesType = %(doctype)s"""

GetBatesNumber = """\
SET NOCOUNT ON;
SELECT TOP 1 bn.*, bt2.* FROM BatesNumber AS bn WITH (NOLOCK)
JOIN DocumentPages AS dp WITH (NOLOCK)
	ON bn.BatesType = bt2.BatesType
WHERE dp.DocumentPageOrder = (
	SELECT TOP 1 DocumentPageOrder FROM DocumentPages WITH (NOLOCK)
		WHERE DocumentID = %(did)s
	ORDER BY DocumentPageOrder)
	AND bn.BatesType = %(batestype)s AND dp.DocumentID = %(did)s"""

GetDocField = """\
SELECT %(sql)s FROM FieldData AS fd WITH (NOLOCK)
JOIN Documents AS d WITH (NOLOCK)
	ON fd.DocumentID = d.DocumentID
WHERE d.DocumentID = %(did)s AND fd.FieldID = %(fieldtype)s"""

GetPickListFieldByID = """\
SELECT %(sql)s FROM PickListEntries AS ple WITH (NOLOCK)
JOIN FieldData AS fd WITH (NOLOCK)
	ON fd.PickListType = ple.PickListType AND fd.PickEntryId = ple.PickListEntryId
WHERE fd.DocumentId = %(did)s AND fd.FieldID = %(fieldid)s"""

GetFieldByName = """\
SELECT %(sql)s FROM FieldData AS fd WITH (NOLOCK)
JOIN Fields AS fld WITH (NOLOCK)
	ON fd.FieldId = fld.FieldId
WHERE fd.DocumentId = %(did)s AND fld.FieldName = '%(fieldname)s'"""

GetPickListFieldByName = """\
SELECT %(sql)s FROM PickListEntries AS ple WITH (NOLOCK)
JOIN FieldData as fd WITH (NOLOCK)
	ON fd.PickListType = ple.PickListType AND fd.PickEntryId = ple.PickEntryId
JOIN Fields AS fl WITH (NOLOCK)
	ON fd.FieldId = fl.FieldId
WHERE fd.DocumentId = %(did)s AND fl.FieldName = '%(fieldname)s'"""

CopyParent = """\
SELECT dip.ParentDocID FROM Documents AS d WITH (NOLOCK)
JOIN DocImportParents AS dip WITH (NOLOCK)
	ON"""
