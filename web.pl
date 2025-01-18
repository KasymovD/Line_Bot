use Dancer2;
use DBI;

set serializer => 'JSON';

my $dsn = "DBI:mysql:database=perl_web;host=localhost";
my $username = "root";
my $password = "";
my $dbh = DBI->connect($dsn, $username, $password, { RaiseError => 1, AutoCommit => 1 });

get '/' => sub {
    template 'index';
};

get '/users' => sub {
    my $sth = $dbh->prepare("SELECT * FROM users");
    $sth->execute();
    my @users;
    while (my $row = $sth->fetchrow_hashref) {
        push @users, $row;
    }
    return \@users;
};

get '/users/:id' => sub {
    my $id = route_parameters->get('id');
    my $sth = $dbh->prepare("SELECT * FROM users WHERE id = ?");
    $sth->execute($id);
    my $user = $sth->fetchrow_hashref;
    return $user;
};

post '/users' => sub {
    my $data = request->data;
    my $name = $data->{name};
    my $email = $data->{email};
    my $sth = $dbh->prepare("INSERT INTO users (name, email) VALUES (?, ?)");
    $sth->execute($name, $email);
    return { status => 'User created' };
};

put '/users/:id' => sub {
    my $id = route_parameters->get('id');
    my $data = request->data;
    my $name = $data->{name};
    my $email = $data->{email};
    my $sth = $dbh->prepare("UPDATE users SET name = ?, email = ? WHERE id = ?");
    $sth->execute($name, $email, $id);
    return { status => 'User updated' };
};

del '/users/:id' => sub {
    my $id = route_parameters->get('id');
    my $sth = $dbh->prepare("DELETE FROM users WHERE id = ?");
    $sth->execute($id);
    return { status => 'User deleted' };
};

get '/users/search/:name' => sub {
    my $name = route_parameters->get('name');
    my $sth = $dbh->prepare("SELECT * FROM users WHERE name LIKE ?");
    $sth->execute("%$name%");
    my @users;
    while (my $row = $sth->fetchrow_hashref) {
        push @users, $row;
    }
    return \@users;
};

get '/users/count' => sub {
    my $sth = $dbh->prepare("SELECT COUNT(*) AS count FROM users");
    $sth->execute();
    my $result = $sth->fetchrow_hashref;
    return $result;
};

patch '/users/:id' => sub {
    my $id = route_parameters->get('id');
    my $data = request->data;
    my @fields;
    my @values;
    if (exists $data->{name}) {
        push @fields, "name = ?";
        push @values, $data->{name};
    }
    if (exists $data->{email}) {
        push @fields, "email = ?";
        push @values, $data->{email};
    }
    return { status => 'No fields to update' } unless @fields;
    my $sql = "UPDATE users SET " . join(", ", @fields) . " WHERE id = ?";
    push @values, $id;
    my $sth = $dbh->prepare($sql);
    $sth->execute(@values);
    return { status => 'User partially updated' };
};

dance;
