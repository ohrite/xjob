# Writer for CDX -- Foxpro Compressed Index
# Eric Ritezel -- January 18, 2007
#

class Write:
	def __init__(self):
		self.startpage = 0
		self.startfreelist = 0
		self.pages = []
		pass

	def _Header(self):
		"""
		Private:
			Write the header
		"""
		# header data
		head = pack('<ll !l <h @BB 486x <hhh 2x s512',
					self.startpage, self.startfreelist, len(self.pages),
					self.options, self.signature, self.sort_order,
					self.total_expr_length, self.for_expr_length,
					self.key_expr_length, self.key_string)

		self.fd.seek(self.adjusted_offset or 0)
		self.fd.write(head)

class Read:
	def __init__(self):
		pass

	def _Header(self):
		if self.dbf is None: raise Exception("No DBF!")

sub read_header {
	my ($self, %opts) = @_;
	$self->{'dbf'} = $opts{'dbf'} if not exists $self->{'dbf'};

	my $header;
	$self->{'fh'}->read($header, 1024) == 1024 or do
		{ __PACKAGE__->Error("Error reading header of $self->{'filename'}: $!\n"); return; };

	@{$self}{ qw( start_page start_free_list total_pages
		key_length index_options index_signature
		sort_order total_expr_length for_expression_length
		key_expression_length
		key_string
		) }
		= unpack 'VVNv CC @502 vvv @510 v @512 a512', $header;

	$self->{'total_pages'} = -1;	### the total_pages value 11
		### that found in rooms.cdx is not correct, so we invalidate it

	($self->{'key_string'}, $self->{'for_string'}) =
		($self->{'key_string'} =~ /^([^\000]*)\000([^\000]*)/);

	$self->{'key_record_length'} = $self->{'key_length'} + 4;
	$self->{'record_len'} = 512;
	$self->{'start_page'} /= $self->{'record_len'};
	$self->{'start_free_list'} /= $self->{'record_len'};
	$self->{'header_len'} = 0;
	$self->{'key_type'} = 0;

## my $out = $self->prepare_write_header;
## if ($out ne $header) {
## 	print STDERR "I won't be able to write the header back\n",
## 	unpack("H*", $out), "\n ++\n",
## 	unpack("H*", $header), "\n";
## }

	if (not defined $self->{'tag'}) {	# top level
		$self->prepare_select;
		while (my ($tag) = $self->fetch) {
			push @{$self->{'tags'}}, $tag;
		}
	}
### use Data::Dumper; print Dumper \%opts;

	if (defined $opts{'tag'}) {
		$self->prepare_select_eq($opts{'tag'});
		my ($foundkey, $value) = $self->fetch;

		if (not defined $foundkey or $opts{'tag'} ne $foundkey) {
			__PACKAGE__->Error("No tag $opts{'tag'} found in index file $self->{'filename'}.\n"); return; };

		my $subidx = bless { %$self }, ref $self;
		print "Adjusting start_page value by $value for $opts{'tag'}\n" if $DEBUG;
		$subidx->{'fh'}->seek($value, 0);
		$subidx->{'adjusted_offset'} = $value;
		$subidx->{'tag'} = $opts{'tag'};
		$subidx->read_header;

		my $key_string = $subidx->{'key_string'};
		my $field_type;
		if (defined $opts{'type'}) {
			$field_type = $opts{'type'};
		}
		elsif (defined $subidx->{'dbf'}) {
			$field_type = $subidx->{'dbf'}->field_type($key_string);
			if (not defined $field_type) {
				__PACKAGE__->Error("Couldn't find key string `$key_string' in dbf file, can't determine field type\n");
				return;
			}
		}
		else {
			__PACKAGE__->Error("Index type (char/numeric) unknown for $subidx\n");
			return;
		}
		$subidx->{'key_type'} = ($field_type =~ /^[NDIF]$/ ? 1 : 0);
		if ($field_type eq 'D') {
			$subidx->{'key_type'} = 2;
			require Time::JulianDay;
		}

		for (keys %$self) { delete $self->{$_} }
		for (keys %$subidx) { $self->{$_} = $subidx->{$_} }
		$self = $subidx;
### use Data::Dumper; print Dumper $self;
	}
	$self;
}

sub last_record {
	shift->{'total_pages'};
}

package XBase::cdx::Page;
use strict;
use vars qw( @ISA $DEBUG );
@ISA = qw( XBase::cdx );

*DEBUG = \$XBase::Index::DEBUG;

# Constructor for the cdx page
sub new {
	my ($indexfile, $num) = @_;
	my $data = $indexfile->read_record($num)
		or do { print $indexfile->errstr; return; };	# get 512 bytes

	my $origdata = $data;

	my ($attributes, $noentries, $left_brother, $right_brother)
		= unpack 'vvVV', $data;		# parse header of the page
	my $keylength = $indexfile->{'key_length'};
	my $keyreclength = $indexfile->{'key_record_length'};	# length

	print "page $num, attr $attributes, noentries $noentries, keylength $keylength (bro $left_brother, $right_brother)\n" if $DEBUG;
	my $numdate = $indexfile->{'key_type'};		# numeric or string?

	my ($keys, $values, $lefts) = ([], [], undef);

	my %opts = ();

	if ($attributes & 2) {
		print "leaf page, compressed\n" if $DEBUG;
		my ($free_space, $recno_mask, $duplicate_count_mask,
		$trailing_count_mask, $recno_count, $duplicate_count,
		$trailing_count, $holding_recno) = unpack '@12 vVCCCCCC', $data;
		print '$free_space, $recno_mask, $duplicate_count_mask, $trailing_count_mask, $recno_count, $duplicate_count, $trailing_count, $holding_recno) = ',
			"$free_space, $recno_mask, $duplicate_count_mask, $trailing_count_mask, $recno_count, $duplicate_count, $trailing_count, $holding_recno)\n" if $DEBUG > 2;

		@opts{ qw! recno_count duplicate_count trailing_count
				holding_recno !  } =
			( $recno_count, $duplicate_count, $trailing_count,
				$holding_recno);

		my $prevkeyval = '';
		for (my $i = 0; $i < $noentries; $i++) {
			my $one_item = substr($data, 24 + $i * $holding_recno, $holding_recno) . "\0" x 4;
			my $numeric_one_item = unpack 'V', $one_item;

			print "one_item: 0x", unpack('H*', $one_item), " ($numeric_one_item)\n" if $DEBUG > 3;

			my $recno = $numeric_one_item & $recno_mask;
			my $bytes_of_recno = int($recno_count / 8);
			$one_item = substr($one_item, $bytes_of_recno);

			$numeric_one_item = unpack 'V', $one_item;
			$numeric_one_item >>= $recno_count - (8 * $bytes_of_recno);

			my $dupl = $numeric_one_item & $duplicate_count_mask;
			$numeric_one_item >>= $duplicate_count;
			my $trail = $numeric_one_item & $trailing_count_mask;
			### $numeric_one_item >>= $trailing_count;

			print "Item $i: trail $trail, dupl $dupl, recno $recno\n" if $DEBUG > 6;

			my $getlength = $keylength - $trail - $dupl;
			my $key = substr($prevkeyval, 0, $dupl);
			$key .= substr($data, -$getlength) if $getlength;
			$key .= "\000" x $trail;
			substr($data, -$getlength) = '' if $getlength;
			$prevkeyval = $key;

### print "Numdate $numdate\n";
			if ($numdate) {		# some decoding for numbers
### print " *** In: ", unpack("H*", $key), "\n";
				if (0x80 & unpack('C', $key)) {
					substr($key, 0, 1) &= "\177";
				}
				else { $key = ~$key; }
				if ($keylength == 8) {
					$key = reverse $key unless $XBase::Index::BIGEND;
					$key = unpack 'd', $key;
				} else {
					$key = unpack 'N', $key;
				}
				if ($numdate == 2 and $key) {	# date
					$key = sprintf "%04d%02d%02d",
						Time::JulianDay::inverse_julian_day($key);
				}
			} else {
				substr($key, -$trail) = '' if $trail;
			}

			print "$key -> $recno\n" if $DEBUG > 4;
			push @$keys, $key;
			push @$values, $recno;
		}
	} else {
		for (my $i = 0; $i < $noentries; $i++) {
			my $offset = 12 + $i * ($keylength + 8);
			my ($key, $recno, $page)
				= unpack "\@$offset a$keylength NN", $data;
			# some decoding for numbers
			if ($numdate) {
				if (0x80 & unpack('C', $key)) {
				### if ("\200" & substr($key, 0, 1)) {
### print STDERR "Declean\n";
### print STDERR unpack("H*", $key), ' -> ';
					substr($key, 0, 1) &= "\177";
### print STDERR unpack("H*", $key), "\n";
				}
				else { $key = ~$key; }
				if ($keylength == 8) {
					$key = reverse $key unless $XBase::Index::BIGEND;
					$key = unpack 'd', $key;
				} else {
					$key = unpack 'N', $key;
				}
				if ($numdate == 2 and $key) {	# date
					$key = sprintf "%04d%02d%02d",
						Time::JulianDay::inverse_julian_day($key);
				}
			} else {
				$key =~ s/\000+$//;
			}
			print "item: $key -> $recno via $page\n" if $DEBUG > 4;
			push @$keys, $key;
			push @$values, $recno;
			$lefts = [] unless defined $lefts;
			push @$lefts, $page / 512;
		}
		$opts{'last_key_is_just_overflow'} = 1;
	}

	my $self = bless { 'keys' => $keys, 'values' => $values,
		'num' => $num, 'keylength' => $keylength,
		'lefts' => $lefts, 'indexfile' => $indexfile,
		'attributes' => $attributes,
		'left_brother' => $left_brother,
		'right_brother' => $right_brother, %opts,
		}, __PACKAGE__;

	my $outdata = $self->prepare_scalar_for_write;
	if (0 and $outdata ne $origdata) {
		print "I won't be able to write this page back.\n",
			unpack("H*", $outdata), "\n ++\n",
			unpack("H*", $origdata), "\n";
	} else {
		### print STDERR " ** Bingo: I will be able to write this page back ($num).\n";
	}

	$self;
}

# Create "new" page -- allocates memory in the file and returns
# structure that can reasonably used as XBase::cdx::Page
sub create {
	my ($class, $indexfile) = @_;
	if (not defined $indexfile and ref $class) {
		$indexfile = $class->{'indexfile'};
	}
	my $fh = $indexfile->{'fh'};
	$fh->seek(0, 2);		# seek to the end;
	my $position = $fh->tell;	# get the length of the file
	if ($position % 512) {
		$fh->print("\000" x (512 - ($position % 512)));
					# pad the file to multiply of 512
		$position = $fh->tell;	# get the length of the file
	}
	$fh->print("\000" x 512);
	return bless { 'num' => $position / 512,
		'keylength' => $indexfile->{'key_length'},
		'indexfile' => $indexfile }, $class;
}

sub prepare_scalar_for_write {
	my $self = shift;

	my ($attributes, $noentries, $left_brother, $right_brother)
		= ($self->{'attributes'}, scalar(@{$self->{'keys'}}),
			$self->{'left_brother'}, $self->{'right_brother'});

	my $data = pack 'vvVV', $attributes, $noentries, $left_brother,
		$right_brother;

	my $indexfile = $self->{'indexfile'};
	my $numdate = $indexfile->{'key_type'};		# numeric or string?
	my $record_len = $indexfile->{'record_len'};
	my $keylength = $self->{'keylength'};

	if ($attributes & 2) {

		my ($recno_count, $duplicate_count, $trailing_count,
					$holding_recno) = (16, 4, 4, 3);
		if (defined $self->{'recno_count'}) {
			($recno_count, $duplicate_count, $trailing_count,
					$holding_recno) =
			@{$self}{ qw! recno_count duplicate_count trailing_count
					holding_recno !  };
		}

### print STDERR "Hmmm. We are setting hardcoded values for bitmasks, not good. Write to adelton.\n";
		my ($recno_mask, $duplicate_mask, $trailing_mask)
			= ( 2**$recno_count - 1, 2**$duplicate_count - 1,
				2**$trailing_count - 1);


		my $recno_data = '';

		my $keys_string = '';
		my $prevkey = '';

		my $row = 0;
		for my $key (@{$self->{'keys'}}) {
			my $dupl = 0;

			my $out = $key;
			# some encoding for numbers
			if ($numdate) {
				if ($keylength == 8) {
					$out = pack 'd', $out;
					$out = reverse $out unless $XBase::Index::BIGEND;
				} else {
					$out = pack 'N', $out;
				}


				unless (0x80 & unpack('C', $out)) {
					substr($out, 0, 1) |= "\200";
				}
				else { $out = ~$out; }
			}

			for my $i (0 .. length($out) - 1) {
				unless (substr($out, $i, 1) eq substr($prevkey, $i, 1)) {
					last;
				}
				$dupl++;
			}

			my $trail = $keylength - length $out;
			while (substr($out, -1) eq "\000") {
				$out = substr($out, 0, length($out) - 1);
				$trail++;
			}
			$keys_string = substr($out, $dupl) . $keys_string;


			my $numdata =
				(((($trail & $trailing_mask) << $duplicate_count)
				| ($dupl & $duplicate_mask)) << $recno_count)
				| ($self->{'values'}[$row] & $recno_mask);

			$recno_data .= substr(pack('V', $numdata), 0, $holding_recno);

			### print unpack("H*", substr($out, $dupl)), ": trail $trail, dupl $dupl\n";

			$prevkey = $out;
			$row++;
		}
		### print $keys_string, "\n";

### print STDERR "Hmmm. The \$numdata is really just a hack -- the shifts have to be made 64 bit clean.\n";
		$data .= pack 'vVCCCCCC',
			($record_len - length($recno_data) - length($keys_string)
				- 24), $recno_mask, $duplicate_mask,
				$trailing_mask, $recno_count, $duplicate_count,
				$trailing_count, $holding_recno;

		$data .= $recno_data;
		$data .= "\000" x ($record_len - length($data) - length($keys_string));
		$data .= $keys_string;
	} else {
		my $row = 0;
		for my $key (@{$self->{'keys'}}) {
			my $out = $key;
			# some encoding for numbers
			if ($numdate) {
				if ($keylength == 8) {
					$out = pack 'd', $out;
					$out = reverse $out unless $XBase::Index::BIGEND;
				} else {
					$out = pack 'N', $out;
				}


				unless (0x80 & unpack('C', $out)) {
					substr($out, 0, 1) |= "\200";
				}
				else { $out = ~$out; }
### print " *** Out2: ", unpack("H*", $out), "\n";
			}
			$data .= pack "a$keylength NN", $out,
				$self->{'values'}[$row],
				$self->{'lefts'}[$row] * 512;
			$row++;
		}
		$data .= "\000" x ($record_len - length($data));
	}
	$data;
}

sub write_page {
	my $self = shift;
	my $indexfile = $self->{'indexfile'};

	my $data = $self->prepare_scalar_for_write;
	die "Data is too long in cdx::write_page for $self->{'num'}\n"
						if length $data > 512;
	$indexfile->write_record($self->{'num'}, $data);
}

# Saves current page, taking into account all neighbour and parent
# pages. We can safely assume that this method is called for pages
# that have been loaded using prepare_select_eq and fetch, so they
# have the parent pointers set correctly.
sub write_with_context {
	my $self = shift;		# page to save
	print STDERR "XBase::cdx::Page::write_with_context called ($self->{'num'})\n" if $DEBUG;

	my $indexfile = $self->{'indexfile'};

	my $self_num = $self->{'num'};

	# get the current page as data to be written
	my $data = $self->prepare_scalar_for_write;

	if (not @{$self->{'keys'}}) {
		$indexfile->write_record($self_num, $data);

		# empty root page means no more work, just save
		return if $self_num == $indexfile->{'start_page'};

		print STDERR "The page $self_num is empty, releasing from the chain\n";

		# first we update the brothers
		my $right_brother_num = $self->{'right_brother'};
		my $left_brother_num = $self->{'left_brother'};
		if ($right_brother_num != 0xFFFFFFFF) {
			my $fix_brother = $indexfile->get_record($right_brother_num / 512);
			$fix_brother->{'left_brother'} = $left_brother_num;
			$fix_brother->write_page;
		}
		if ($left_brother_num != 0xFFFFFFFF) {
			my $fix_brother = $indexfile->get_record($left_brother_num / 512);
			$fix_brother->{'right_brother'} = $right_brother_num;
			$fix_brother->write_page;
		}

		# now we need to release ourselves from parent as well
		my $parent = $self->get_parent_page or die "Index corrupt: no parent for page $self ($self_num)\n";

		my $maxindex = $#{$parent->{'lefts'}};
		my $i;
		for ($i = 0; $i <= $maxindex; $i++) {
			if ($parent->{'lefts'}[$i] == $self_num) {
				splice @{$parent->{'keys'}}, $i, 1;
				splice @{$parent->{'values'}}, $i, 1;
				splice @{$parent->{'lefts'}}, $i, 1;
				last;
			}
		}
		if ($i > $maxindex) {
			die "Index corrupt: parent doesn't point to us in write_with_context $self ($self_num)\n";
		}
		$parent->write_with_context;
		return;
	}


	if (length $data > 512) {	# we need to split the page
		print STDERR "Splitting full page $self ($self_num)\n";

		# create will give us brand new empty page

		my $new_page = __PACKAGE__->create($indexfile);
		$self->{'attributes'} &= 0xfffe;
		$new_page->{'attributes'} = $self->{'attributes'};

		my $total_rows = scalar(@{$self->{'keys'}});
		my $half_rows = int($total_rows / 2);

		# primary split
		if ($half_rows == 0) { $half_rows++; }
		if ($half_rows == $total_rows) {
			die "Fatal trouble: page $self ($self_num) is full but I'm not able to split it\n";
		}

		# new page is right brother (will get bigger values)
		$new_page->{'right_brother'} = $self->{'right_brother'};
		$new_page->{'left_brother'} = $self_num * 512;
		$self->{'right_brother'} = $new_page->{'num'} * 512;

		if ($new_page->{'right_brother'} != 0xFFFFFFFF) {
			my $fix_brother = $indexfile->get_record($new_page->{'right_brother'} / 512);
			$fix_brother->{'left_brother'} = $new_page->{'num'} * 512;
			$fix_brother->write_page;
		}

		# we'll split keys and values
		$new_page->{'keys'} = [ @{$self->{'keys'}}[$half_rows .. $total_rows - 1] ];
		splice @{$self->{'keys'}}, $half_rows, $total_rows - $half_rows;
		$new_page->{'values'} = [ @{$self->{'values'}}[$half_rows .. $total_rows - 1] ];
		splice @{$self->{'values'}}, $half_rows, $total_rows - $half_rows;

		# and we'll split pointers to lower levels, if there are any
		if (defined $self->{'lefts'}) {
			$new_page->{'lefts'} = [ @{$self->{'lefts'}}[$half_rows ..  $total_rows - 1] ];
			my $new_page_num = $new_page->{'num'};
			for my $q (@{$new_page->{'lefts'}}) {
				if (defined $q and defined $indexfile->{'pages_cache'}{$q}) {
					$indexfile->{'pages_cache'}{$q}{'parent'} = $new_page_num;
				}
			}
			splice @{$self->{'lefts'}}, $half_rows, $total_rows - $half_rows - 1;
		}

		my $parent;
		if ($self_num == $indexfile->{'start_page'}) {
			# we're splitting the root page, so we will
			# create new one
			$parent = __PACKAGE__->create($indexfile);

			$indexfile->{'start_page'} = $parent->{'num'};
			$indexfile->write_header;

			### xxxxxxxxxxxxxxxxxxx
			### And here we should write the header so that
			### the new root page is saved to disk. Not
			### tested yet.
			### xxxxxxxxxxxxxxxxxxx

			$parent->{'attributes'} = 1;	# root page

			$parent->{'keys'} = [ $self->{'keys'}[-1],
						$new_page->{'keys'}[-1] ];
			$parent->{'values'} = [ $self->{'values'}[-1],
						$new_page->{'values'}[-1] ];
			$parent->{'lefts'} = [ $self_num, $new_page->{'num'} ];
		} else {	# update pointers in parent page
			$parent = $self->get_parent_page or die "Index corrupt: no parent for page $self ($self_num)\n";
			my $maxindex = $#{$parent->{'lefts'}};
			my $i = 0;

			# find pointer to ourselves in the parent
			while ($i <= $maxindex) {
				last if $parent->{'lefts'}[$i] == $self_num;
				$i++;
			}

			if ($i > $maxindex) {
				die "Index corrupt: parent doesn't point to us in write_with_context $self ($self_num)\n";
			}

			# now $i is index in parent of the record pointing to us

			splice @{$parent->{'keys'}}, $i, 1,
				$self->{'keys'}[-1], $new_page->{'keys'}[-1];
			splice @{$parent->{'values'}}, $i, 1,
				$self->{'values'}[-1], $new_page->{'values'}[-1];
			splice @{$parent->{'lefts'}}, $i, 1,
				$self_num, $new_page->{'num'};
		}

		$self->write_page;

		$new_page->{'parent'} = $self->{'parent'};
		$new_page->write_page;

		$parent->write_with_context;
	}
	elsif ($self_num != $indexfile->{'start_page'}) {
		# the output data is OK, write is out
		# but this is not root page, so we need to make sure the
		# parent is updated as well
		$indexfile->write_record($self_num, $data);

		# now we need to check if the parent page still points
		# correctly to us (the last value might have changed)
		my $parent = $self->get_parent_page or die "Index corrupt: no parent for page $self ($self_num)\n";

		my $maxindex = $#{$parent->{'lefts'}};
		my $i = 0;

		# find pointer to ourselves in the parent
		while ($i <= $maxindex) {
			last if $parent->{'lefts'}[$i] == $self_num;
			$i++;
		}

		if ($i > $maxindex) {
			die "Index corrupt: parent doesn't point to us in write_with_context $self ($self_num)\n";
		}

		# now $i is index in parent of the record pointing to us

		if ($parent->{'values'}[$i] != $self->{'values'}[-1]) {
			print STDERR "Will need to update the parent -- last value in myself changed ($self_num)\n";
			$parent->{'values'}[$i] = $self->{'values'}[-1];
			$parent->{'keys'}[$i] = $self->{'keys'}[-1];
			$parent->write_with_context;
		}

	} else {	# write out root page
		$indexfile->write_record($self_num, $data);
	}

	print STDERR "XBase::cdx::Page::write_with_context finished ($self->{'num'})\n" if $DEBUG;
}

# finds parent page for the object
sub get_parent_page_num {
	my $self = shift;
	return $self->{'parent'} if defined $self->{'parent'};

	my $indexfile = $self->{'indexfile'};

	return if $self->{'num'} == $indexfile->{'start_page'};

	# this should search to this page, effectivelly setting the
	# level array in such a way that the parent page is there
	$indexfile->prepare_select_eq($self->{'keys'}[0], $self->{'values'}[0]);

### print STDERR "self($self->{'num'}): $self, pages: @{$indexfile->{'pages'}}\n";
### use Data::Dumper; print Dumper $indexfile;
	my $pageindex = $#{$indexfile->{'pages'}};
	while ($pageindex >= 0) {
		if ("$self" eq "$indexfile->{'pages'}[$pageindex]") {
			print STDERR "Parent page for $self->{'num'} is $indexfile->{'pages'}[$pageindex - 1]{'num'}.\n";
			return $indexfile->{'pages'}[$pageindex - 1]->{'num'};
		}
		$pageindex--;
	}
	return undef;
}
sub get_parent_page {
	my $self = shift;
	my $parent_num = $self->get_parent_page_num or return;
	my $indexfile = $self->{'indexfile'};
	return $indexfile->get_record($parent_num);
	}

1;