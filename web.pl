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
    return to_json(\@users);
};

get '/users/:id' => sub {
    my $id = route_parameters->get('id');
    my $sth = $dbh->prepare("SELECT * FROM users WHERE id = ?");
    $sth->execute($id);
    my $user = $sth->fetchrow_hashref;
    return to_json($user);
};

post '/users' => sub {
    my $data = request->data;
    my $name = $data->{name};
    my $email = $data->{email};
    my $sth = $dbh->prepare("INSERT INTO users (name, email) VALUES (?, ?)");
    $sth->execute($name, $email);
    return to_json({ status => 'User created' });
};

put '/users/:id' => sub {
    my $id = route_parameters->get('id');
    my $data = request->data;
    my $name = $data->{name};
    my $email = $data->{email};
    my $sth = $dbh->prepare("UPDATE users SET name = ?, email = ? WHERE id = ?");
    $sth->execute($name, $email, $id);
    return to_json({ status => 'User updated' });
};

del '/users/:id' => sub {
    my $id = route_parameters->get('id');
    my $sth = $dbh->prepare("DELETE FROM users WHERE id = ?");
    $sth->execute($id);
    return to_json({ status => 'User deleted' });
};

dance;
